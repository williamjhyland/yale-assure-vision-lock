# KasaSmartPlugVisionActivation/src/KasaSmartPlugVisionActivation.py
import asyncio

import os
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
    MODEL: ClassVar[Model] = Model(ModelFamily("acme","memory_sensor"), "rasppi")
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
        actual_cam_name = config.attributes.fields["actual_cam"].string_value
        actual_cam = dependencies[Camera.get_resource_name(actual_cam_name)]
        self.source_camera = cast(Camera, actual_cam)

        vision_service_name = config.attributes.fields["vision_service"].string_value
        vision_service = dependencies[Vision.get_resource_name(vision_service_name)]
        self.vision_service = cast(Vision, vision_service)

        tags = config.attributes.fields["tags"].string_value
        self.tags = tags

        plug_ip = config.attributes.fields["plug_ip"].string_value
        self.plug = SmartPlug(plug_ip)

        if config.attributes.fields["default_state"].string_value.lower() == "on" or config.attributes.fields["default_state"].string_value.lower() == "off":
            default_state = config.attributes.fields["default_state"].string_value.lower()
            self.default_state = default_state
        else:
            self.default_state = "on"

        logger.info("reconfigured")

    async def get_readings(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Mapping[str, Any]:
        await self.check_kasa_plug()
        sensor_reading = await self.call_kasa()
        return sensor_reading
    
    async def check_kasa_plug(self):
        found = False
        detections = await self.vision_service.get_detections_from_camera("webcam")
        for d in detections:
            if d.confidence >= self.tags.get(d) and self.tags.get(d) != None:
                print("I see a " + str(d.class_name))
                found = True
                break

        if found == True:
            if self.default_state == "on":
                self.plug.turn_off()
            else:
                self.plug.turn_on()
        else:
            if self.default_state == "on":
                self.plug.turn_on()
            else:
                self.plug.turn_off()
        pass

    async def call_kasa(self):
        found_devices = await Discover.discover()
        return found_devices


# Anything below this line is optional, but may come in handy for debugging and testing.
# To use, call `python wifi_sensor.py` in the command line while in the `src` directory.
async def main():
    plug = MySensor(name="plug")
    readings = await plug.get_readings()
    print(readings)

if __name__ == '__main__':
    asyncio.run(main())