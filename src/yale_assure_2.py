# Yale Smart Lock Vision/src/Yale Smart Lock Vision.py
import asyncio
import json
import threading
import time

from typing import ClassVar, Mapping, Sequence, Optional, Any, Dict, cast
from typing_extensions import Self
from google.protobuf import json_format
from PIL import Image

from august.api import Api 
from august.authenticator import Authenticator, AuthenticationState, ValidationResult
from august.lock import LockStatus

from viam.components.camera import Camera
from viam.components.sensor import Sensor
from viam.errors import NoCaptureToStoreError
from viam.logging import getLogger
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily
from viam.services.vision import Vision
from viam.utils import struct_to_dict

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
        if self.lock is not None:
            self.lock_status = self.api.get_lock_status(self.access_token, self.lock.device_id)
            self.last_check = time.localtime()
        else:
            logger.error("Lock object is None. Cannot update lock status.")

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
        attributes_dict = struct_to_dict(config.attributes)
        """Validates JSON configuration"""
        
        required_attributes = ["actual_cam", "vision_service", "tags", "lock_name", "access_token_path"]

        for attribute in required_attributes:
            if attribute not in attributes_dict or not attributes_dict[attribute].string_value.strip():
                raise Exception(f"{attribute} attribute is required for a Yale Smart Lock Vision component")
                
        return []
        
    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        """Handles attribute reconfiguration"""
        attributes_dict = struct_to_dict(config.attributes)
        # Retrieve authentication configuration and set as attributes
        self.authentication_method = "email"

        # Extract required attributes using attributes_dict
        self.access_token_path = attributes_dict["access_token_path"]

        actual_cam_name = attributes_dict["source_camera"]
        self.source_camera = cast(Camera, dependencies[Camera.get_resource_name(actual_cam_name)])

        vision_service_name = attributes_dict["vision_service"]
        self.vision_service = cast(Vision, dependencies[Vision.get_resource_name(vision_service_name)])

        self.lock_name = attributes_dict["lock_name"]

        if attributes_dict["default_state"].lower() == "locked" or attributes_dict["default_state"].lower() == "unlocked":
            self.default_state = attributes_dict["default_state"].lower()
        else:
            self.default_state = "locked"

        if "auth_username" not in attributes_dict or "auth_password" not in attributes_dict:
            self.auth_username = "EMAIL@EMAIL.COM"
            self.auth_password = "PASSWORD"
        else:
            self.auth_username = attributes_dict["auth_username"]
            self.auth_password = attributes_dict["auth_password"]

        api = Api(timeout=20)
        access_token_cache_file_path = self.access_token_path
        authenticator = Authenticator(
            api, 
            self.authentication_method, 
            self.auth_username, 
            self.auth_password, 
            access_token_cache_file=access_token_cache_file_path)        
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
                logger.warn(f"**** Locks: {locks!r} ****")
                for lock in locks:
                    if lock.device_name == self.lock_name:
                        selected_lock = lock
                        break

                logger.warn("**** Creating Lock Controller ****")
                logger.warn(f"**** Selected Lock: {selected_lock!r} ****")
                if selected_lock is not None:
                    self.lock_controller = LockController(api, access_token, selected_lock)
                    self.lock_controller.start()
                else:
                    logger.warn(f"**** Selected lock can't be None... ****")
                    self.lock_controller = LockController()

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

if __name__ == '__main__':
    asyncio.run(main())