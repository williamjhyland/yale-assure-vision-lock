# KasaSmartPlugVisionActivation/src/KasaSmartPlugVisionActivation.py
import asyncio
import json
from typing import ClassVar, Mapping, Sequence, Optional, Dict, Any, cast
from google.protobuf import json_format
from kasa import SmartPlug, Discover
from viam.components.sensor import Sensor
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily
from viam.services.vision import Vision
from viam.components.camera import Camera
from viam.errors import NoCaptureToStoreError
from viam.logging import getLogger

logger = getLogger(__name__)

class MySensor(Sensor):
    MODEL: ClassVar[Model] = Model(ModelFamily("bill", "kasaplug"), "visionswitch")
    
    def __init__(self, name: str):
        super().__init__(name)
        self.source_camera = None
        self.tags = None
        self.vision_service = None
        self.plug_ip = None
        self.plug = None
        self.default_state = "on"

    @classmethod
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
        required_fields = ["actual_cam", "vision_service", "tags", "plug_ip"]
        return [config.attributes.fields[field].string_value for field in required_fields if config.attributes.fields[field].string_value]

    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        self.source_camera = cast(Camera, dependencies[Camera.get_resource_name(config.attributes.fields["source_camera"].string_value)])
        self.vision_service = cast(Vision, dependencies[Vision.get_resource_name(config.attributes.fields["vision_service"].string_value)])
        self.tags = json.loads(json_format.MessageToJson(config.attributes.fields["tags"]))
        self.plug = SmartPlug(config.attributes.fields["plug_ip"].string_value)
        self.default_state = config.attributes.fields["default_state"].string_value.lower()

    async def get_readings(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Mapping[str, Any]:
        await self.check_kasa_plug()
        if extra and extra.get('fromDataManagement'):
            raise NoCaptureToStoreError()
        else:
            return await self.discover_kasa_devices()

    async def check_kasa_plug(self):
        detections = await self.vision_service.get_detections_from_camera("webcam")
        found = any(self.tags.get(d.class_name) is not None and d.confidence >= self.tags[d.class_name] for d in detections)
        
        if found:
            await getattr(self.plug, 'turn_off' if self.default_state == "on" else 'turn_on')()
        else:
            await getattr(self.plug, 'turn_on' if self.default_state == "on" else 'turn_off')()

    async def discover_kasa_devices(self):
        devices = await Discover.discover()
        return {addr: f"<DeviceType.{dev.device_type.name} model {dev.model} at {addr} ({dev.alias}), is_on: {dev.is_on}" for addr, dev in devices.items()}

async def main():
    found_devices = await Discover.discover()
    print(found_devices)

if __name__ == '__main__':
    asyncio.run(main())
