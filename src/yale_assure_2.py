# Yale Smart Lock Vision/src/Yale Smart Lock Vision.py
import asyncio
import json
import time
import threading
import requests
from google.protobuf import json_format

from august.api import Api 
from august.authenticator import Authenticator, AuthenticationState, ValidationResult
from august.lock import LockStatus

from typing import ClassVar, Mapping, Sequence, Optional, cast, Tuple, List, Any, Dict
from typing_extensions import Self

from viam.components.sensor import Sensor
from viam.operations import run_with_operation
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily
from viam.services.vision import VisionClient

from viam.module.types import Reconfigurable
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName, ResponseMetadata, Geometry
from viam.components.camera import Camera
from viam.resource.types import Model, ModelFamily
from viam.resource.base import ResourceBase
from viam.media.video import NamedImage
from viam.errors import NoCaptureToStoreError

from PIL import Image

from viam.services.vision import Vision

from viam.logging import getLogger

logger = getLogger(__name__)

class LockController(threading.Thread):
    def __init__(self, api=None, access_token=None, lock=None):
        threading.Thread.__init__(self)
        self.api = api
        self.access_token = access_token
        self.lock = lock
        self.lock_status = LockStatus.UNKNOWN
        self.daemon = True  # Set as a daemon so it will be killed once the main program exits
        self.lock_action = None
        self.locks = []
        self.running = True
        self.error_messages = ""
        self.last_check = ""
        self.backoff_time = 15

    def run(self):
        max_backofftime = 300
        while self.running:
            try:
                while self.get_lock_status() == LockStatus.UNKNOWN:
                    logger.warn("--- Getting Lock Status ---")
                    self._update_lock_status()
                    if self.get_lock_status() == LockStatus.UNKNOWN:
                        logger.warn("--- Lock Status UNKNOWN Try Again in %s seconds! ---", self.backoff_time)
                        time.sleep(self.backoff_time)
                    if self.backoff_time <= max_backofftime:
                        self.backoff_time = min(self.backoff_time * 2, max_backofftime)

                self.backoff_time = 15
                self._update_lock_status()
                # Perform any pending lock action
                if self.lock_action == "lock" and self.get_lock_status() == LockStatus.UNLOCKED:
                    logger.warn("--------- TRY LOCKING @ %s ---------", str(time.strftime("%B %d, %Y %H:%M:%S",self.last_check)))
                    self.api.lock(self.access_token, self.lock.device_id)
                elif self.lock_action == "unlock" and self.get_lock_status() == LockStatus.LOCKED:
                    logger.warn("--------- TRY UNLOCKING @ %s ---------", str(time.strftime("%B %d, %Y %H:%M:%S",self.last_check)))
                    self.api.unlock(self.access_token, self.lock.device_id)
                else:
                    logger.warn("--------- LOCK IS PROPERLY SET @ %s ---------", str(time.strftime("%B %d, %Y %H:%M:%S",self.last_check)))
                    
                    time.sleep(1)
            except Exception as e:
                logger.error("Error in thread: %s", str(e))
                self.error_messages = str(e)
                self._update_lock_status()
                time.sleep(30)  # Pause for 5 seconds between checks

    def set_lock_action(self, action):
        self.lock_action = action

    def get_lock_status(self):
        return self.lock_status

    def _update_lock_status(self):
        # This method updates the lock status and logs the time
        self.lock_status = self.api.get_lock_status(self.access_token, self.lock.device_id)
        self.last_check = time.localtime()

    def get_last_action(self):
        return self.lock_action

    def get_last_error(self):
        return self.error_messages

    def get_last_check_time(self):
        return self.last_check

    def get_last_backoff_time(self):
        return str(self.backoff_time)
    
    def get_locks(self):
        return self.locks

    def stop(self):
        self.running = False

class MySensor(Sensor):
    # Subclass the Viam Sensor component and implement the required functions
    MODEL: ClassVar[Model] = Model(ModelFamily("bill","yalesmartlock"), "visionswitch")
    
    @classmethod
    def new(cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        sensor = cls(config.name)
        sensor.reconfigure(config, dependencies)
        return sensor

    @classmethod
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
        """Validates JSON configuration"""
        
        source_camera = config.attributes.fields["actual_cam"].string_value
        if source_camera == "":
            raise Exception("actual_cam attribute is required for a Yale Smart Lock Vision component")
        
        vision_service = config.attributes.fields["vision_service"].string_value
        if vision_service == "":
            raise Exception("vision_service attribute is required for a Yale Smart Lock Vision component")
    
        tags = config.attributes.fields["tags"]
        if tags == "":
            raise Exception("tags attribute is required for a Yale Smart Lock Vision component")
        
        lock_name = config.attributes.fields["lock_name"].string_value
        if lock_name == "":
            raise Exception("lock_name attribute is required for a Yale Smart Lock Vision component")
        
        authentication_method = config.attributes.fields["authentication_method"].string_value
        if authentication_method.lower() != "email" or authentication_method.lower() != "phone":
            raise Exception("authentication_method attribute is required for a Yale Smart Lock Vision component")

        auth_username = config.attributes.fields["auth_username"].string_value
        if auth_username == "":
            raise Exception("auth_username attribute is required for a Yale Smart Lock Vision component")

        auth_password = config.attributes.fields["auth_password"].string_value
        if auth_password == "":
            raise Exception("auth_password attribute is required for a Yale Smart Lock Vision component")

        access_token_path = config.attributes.fields["access_token_path"].string_value
        if access_token_path == "":
            raise Exception("access_token_path attribute is required for a Yale Smart Lock Vision component")

        return []
        
    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        """Handles attribute reconfiguration"""
        # Retrieve authentication configuration and set as attributes
        self.authentication_method = config.attributes.fields["authentication_method"].string_value
        self.auth_username = config.attributes.fields["auth_username"].string_value
        self.auth_password = config.attributes.fields["auth_password"].string_value
        self.access_token_path = config.attributes.fields["access_token_path"].string_value

        actual_cam_name = config.attributes.fields["source_camera"].string_value
        actual_cam = dependencies[Camera.get_resource_name(actual_cam_name)]
        self.source_camera = cast(Camera, actual_cam)

        vision_service_name = config.attributes.fields["vision_service"].string_value
        vision_service = dependencies[Vision.get_resource_name(vision_service_name)]
        self.vision_service = cast(Vision, vision_service)

        self.lock_name = config.attributes.fields["lock_name"].string_value

        tags = config.attributes.fields["tags"]
        tags = json.loads(json_format.MessageToJson(config.attributes.fields["tags"]))

        self.tags = tags


        if config.attributes.fields["default_state"].string_value.lower() == "locked" or config.attributes.fields["default_state"].string_value.lower() == "unlocked":
            default_state = config.attributes.fields["default_state"].string_value.lower()
            self.default_state = default_state
        else:
            self.default_state = "locked"

        api = Api(timeout=20)
        access_token_cache_file_path = '/home/viam/yale-assure-vision-lock/src/accesstoken/august_access_token.json'
        authenticator = Authenticator(api, "email", "bill.hyland@viam.com", "Password123!", access_token_cache_file=access_token_cache_file_path)
        authentication = authenticator.authenticate()

        if authentication.state == AuthenticationState.AUTHENTICATED:
            logger.warn("**** Authentication State Authenticated ****")
            with open(access_token_cache_file_path, 'r') as file:
                data = json.load(file)
                access_token = data["access_token"]

            locks = api.get_locks(authentication.access_token)
            if not locks:
                print("No locks found.")
            else:
                # Finding the lock by name
                selected_lock = None
                for lock in locks:
                    if lock.device_name == self.lock_name:
                        selected_lock = lock
                        break

                self.lock_controller = LockController(api, access_token, selected_lock)
                self.lock_controller.start()

                for lock in locks:
                    self.lock_controller.locks.append(lock.device_name)
        else:
            logger.warn("**** Authentication State NOT Authenticated ****")
            self.lock_controller = LockController()


    async def get_readings(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Mapping[str, Any]:
        if self.lock_controller is None or not self.lock_controller.is_alive():
            # Lock Controller is not started or not running
            return {"status": "Lock Controller not started", "locks": []}
        
        if self.lock_controller.locks is None:
            # No locks are detected
            return {"status": "No locks detected", "locks": []}

        if 'fromDataManagement' in extra and extra['fromDataManagement'] is True:
            await self.check_yale_lock()
            raise NoCaptureToStoreError()
        else:
            if self.lock_controller.get_lock_status() == None:
                logger.warn("--- Lock Status Unknown... Setting to None ---")
                lock_state = "None"
            else:
                lock_state = self.lock_controller.get_lock_status().name
            sensor_reading = {
                "Locks Available": self.lock_controller.locks, 
                "Thread Alive": self.lock_controller.is_alive(), 
                "Lock Action": self.lock_controller.get_last_action(), 
                "Lock Status": lock_state,
                "Last Error Message": self.lock_controller.get_last_error(),
                "Last Check Timestamp": str(time.strftime("%B %d, %Y %H:%M:%S", self.lock_controller.get_last_check_time())),
                "Last Back Off Time": self.lock_controller.get_last_backoff_time()
                }
            return sensor_reading
    
    async def check_yale_lock(self):
        found = False
        detections = await self.vision_service.get_detections_from_camera(self.source_camera.name)
        for d in detections:
            tag_value = self.tags.get(d.class_name)
            if tag_value is not None and d.confidence >= tag_value:
                found = True
                break

        if found == True:
            if self.default_state == "locked":
                self.lock_controller.lock_action = "unlock"
            else:
                self.lock_controller.lock_action = "lock"
        else:
            if self.default_state == "locked":
                self.lock_controller.lock_action = "lock"
            else:
                self.lock_controller.lock_action = "unlock"
        pass

# Anything below this line is optional, but may come in handy for debugging and testing.
async def main():
    return None 

    api = Api(timeout=20)
    access_token_cache_file_path = '/home/viam/yale-assure-vision-lock/src/accesstoken/august_access_token.json'
    authenticator = Authenticator(api, "email", "bill.hyland@viam.com", "Password123!", access_token_cache_file=access_token_cache_file_path)
    # authenticator = Authenticator(api, "phone", "+14406104434", "Password123!", access_token_cache_file=access_token_cache_file)

    # Attempt to authenticate from cache
    authentication = authenticator.authenticate()

    print(authentication.state)

    if authentication.state == AuthenticationState.AUTHENTICATED:
        with open(access_token_cache_file_path, 'r') as file:
            data = json.load(file)
            access_token = data["access_token"]

        locks = api.get_locks(authentication.access_token)
        if not locks:
            print("No locks found.")
            exit()

        print(locks)

        

        lock = locks[0]
        lock_controller = LockController(api, access_token, lock)
        lock_controller.start()

        while True:
            while lock_controller.get_lock_status() == LockStatus.UNKNOWN:
                print(lock_controller.get_lock_status())
                time.sleep(3)
            print(lock_controller.get_lock_status(), lock_controller.get_last_action(), lock_controller.get_lock_status() == LockStatus.LOCKED, lock_controller.get_lock_status() == LockStatus.UNLOCKED)
            if lock_controller.get_lock_status() == LockStatus.LOCKED:
                lock_controller.set_lock_action("unlock")
            elif lock_controller.get_lock_status() == LockStatus.UNLOCKED:
                lock_controller.set_lock_action("lock")
            time.sleep(3)  # Check every 3 seconds
    elif authentication.state == AuthenticationState.REQUIRES_VALIDATION:
        print("Validation required. Sending verification code...")
        authenticator.send_verification_code()
        verification_code = input("Enter verification code: ")  # Prompt user for verification code
        validation_result = authenticator.validate_verification_code(verification_code)

        if validation_result == ValidationResult.VALIDATED:
            print("Validation successful. Re-authenticating...")
            authentication = authenticator.authenticate()  # Re-authenticate after validation
        else:
            print("Invalid verification code. Please try again.")
            # Handle invalid verification code scenario

if __name__ == '__main__':
    asyncio.run(main())