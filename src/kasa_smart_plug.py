# KasaSmartPlugVisionActivation/src/KasaSmartPlugVisionActivation.py
import asyncio

import os
import json
from google.protobuf import json_format

from kasa import SmartPlug
from kasa import Discover

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
from viam.errors import NoCaptureToStoreError
from viam.services.vision import Vision
from viam.utils import from_dm_from_extra


import kasa
from viam.logging import getLogger

logger = getLogger(__name__)

class MySensor(Sensor):
    # Subclass the Viam Sensor component and implement the required functions
    MODEL: ClassVar[Model] = Model(ModelFamily("bill","kasaplug"), "visionswitch")
    source_camera = None
    tags = None
    vision_service = None
    plug_ip = None
    
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
            raise Exception("actual_cam attribute is required for a KasaSmartPlugVisionActivation component")
        
        vision_service = config.attributes.fields["vision_service"].string_value
        if vision_service == "":
            raise Exception("vision_service attribute is required for a KasaSmartPlugVisionActivation component")
    
        tags = config.attributes.fields["tags"]
        if tags == "":
            raise Exception("tags attribute is required for a KasaSmartPlugVisionActivation component")
        
        plug_ip = config.attributes.fields["plug_ip"].string_value
        if plug_ip == "":
            raise Exception("plug_ip attribute is required for a KasaSmartPlugVisionActivation component")
        
        return [source_camera, vision_service, tags, plug_ip]
        
    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        """Handles attribute reconfiguration"""
        actual_cam_name = config.attributes.fields["source_camera"].string_value
        actual_cam = dependencies[Camera.get_resource_name(actual_cam_name)]
        self.source_camera = cast(Camera, actual_cam)

        vision_service_name = config.attributes.fields["vision_service"].string_value
        vision_service = dependencies[Vision.get_resource_name(vision_service_name)]
        self.vision_service = cast(Vision, vision_service)

        tags = config.attributes.fields["tags"]
        tags = json.loads(json_format.MessageToJson(config.attributes.fields["tags"]))

        self.tags = tags

        plug_ip = config.attributes.fields["plug_ip"].string_value
        self.plug = SmartPlug(plug_ip)

        if config.attributes.fields["default_state"].string_value.lower() == "on" or config.attributes.fields["default_state"].string_value.lower() == "off":
            default_state = config.attributes.fields["default_state"].string_value.lower()
            self.default_state = default_state
        else:
            self.default_state = "on"

    async def get_readings(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Mapping[str, Any]:
        await self.check_kasa_plug()
        if 'fromDataManagement' in extra and extra['fromDataManagement'] is True:
            sensor_reading = {'value': 'NOT READY'}
        else:
            sensor_reading = await self.discover_kasa_devices()
        return sensor_reading
    
    async def check_kasa_plug(self):
        found = False
        detections = await self.vision_service.get_detections_from_camera("webcam")
        for d in detections:
            tag_value = self.tags.get(d.class_name)
            if tag_value is not None and d.confidence >= tag_value:
                print("I see a " + str(d.class_name))
                found = True
                break

        if found == True:
            if self.default_state == "on":
                await self.plug.turn_off()
            else:
                await self.plug.turn_on()
        else:
            if self.default_state == "on":
                await self.plug.turn_on()
            else:
                await self.plug.turn_off()
        pass

    async def discover_kasa_devices(self):
        devices = await Discover.discover()
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
    found_devices = await Discover.discover()
    print(found_devices)
    print(type(found_devices))

if __name__ == '__main__':
    asyncio.run(main())