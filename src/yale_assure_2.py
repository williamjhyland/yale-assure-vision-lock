# Yale Smart Lock Vision/src/Yale Smart Lock Vision.py
import asyncio
import json
import time
import threading
import requests

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
from PIL import Image

from viam.services.vision import Vision

from viam.logging import getLogger

logger = getLogger(__name__)

class LockController(threading.Thread):
    def __init__(self, api, access_token, lock):
        threading.Thread.__init__(self)
        self.api = api
        self.access_token = access_token
        self.lock = lock
        self.lock_status = LockStatus.UNKNOWN
        self.daemon = True  # Set as a daemon so it will be killed once the main program exits
        self.lock_action = None

    def run(self):
        while True:
            # Check and update the lock status
            self.lock_status = self.api.get_lock_status(self.access_token, self.lock.device_id)

            # Perform any pending lock action
            if self.lock_action == "lock" and self.lock_status == LockStatus.UNLOCKED:
                self.api.lock(self.access_token, self.lock.device_id)
                time.sleep(3)
            elif self.lock_action == "unlock" and self.lock_status == LockStatus.LOCKED:
                self.api.unlock(self.access_token, self.lock.device_id)
                time.sleep(3)
            
            self.lock_action = None
            time.sleep(1)  # Pause for 5 seconds between checks

    def set_lock_action(self, action):
        self.lock_action = action

    def get_lock_status(self):
        return self.lock_status

    def get_last_action(self):
        return self.lock_action

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
        access_token_cache_file_path = '/Users/williamhyland/Documents/Projects/py-august/accesstoken/august_access_token.json'
        authenticator = Authenticator(api, "email", "bill.hyland@viam.com", "Password123!", access_token_cache_file=access_token_cache_file_path)
        authentication = authenticator.authenticate()

        if authentication.state == AuthenticationState.AUTHENTICATED:
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
                    if lock.name == self.lock_name:
                        selected_lock = lock
                        break

                self.lock_controller = LockController(api, access_token, selected_lock)
                self.lock_controller.start()

    async def get_readings(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Mapping[str, Any]:
        await self.check_yale_lock()
        if 'fromDataManagement' in extra and extra['fromDataManagement'] is True:
            raise NoCaptureToStoreError()
        else:
            sensor_reading = await self.discover_yale_devices()
        return sensor_reading
    
    async def check_yale_lock(self):
        found = False
        detections = await self.vision_service.get_detections_from_camera(self.source_camera.name)
        for d in detections:
            tag_value = self.tags.get(d.class_name)
            if tag_value is not None and d.confidence >= tag_value:
                print("I see a " + str(d.class_name))
                found = True
                break

        if found == True:
            if self.default_state == "locked":
                self.lock_controller.lock_action = "unlock"
            else:
                self.lock_controller.lock_action = "lock"
        else:
            if self.default_state == "unlocked":
                self.lock_controller.lock_action = "lock"
            else:
                self.lock_controller.lock_action = "unlock"
        pass

    async def discover_yale_devices(self):
        devices = api.get_locks()
        device_dict = {}

        for addr, dev in devices.items():
            await dev.update()  # Update device state

            # Format the device information
            device_info = f"<DeviceType.{dev.device_type.name} model {dev.model} at {addr} ({dev.alias}), is_on: {dev.is_on}"

            # Add to dictionary
            device_dict[addr] = device_info

        return device_dict


# Anything below this line is optional, but may come in handy for debugging and testing.
async def main():
    api = Api(timeout=20)
    access_token_cache_file_path = '/Users/williamhyland/Documents/Projects/py-august/accesstoken/august_access_token.json'
    authenticator = Authenticator(api, "email", "bill.hyland@viam.com", "Password123!", access_token_cache_file=access_token_cache_file_path)
    # authenticator = Authenticator(api, "phone", "+14406104434", "Password123!", access_token_cache_file=access_token_cache_file)

    # Attempt to authenticate from cache
    authentication = authenticator.authenticate()

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

        lock_status = lock_controller.get_lock_status()

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

if __name__ == '__main__':
    asyncio.run(main())