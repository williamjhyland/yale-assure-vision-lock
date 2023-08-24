# wifi-sensor/src/wifi_sensor.py
import asyncio
from typing import Any, ClassVar, Dict, Mapping, Optional, Sequence, Tuple
from typing_extensions import Self

from viam.components.sensor import Sensor
from viam.operations import run_with_operation
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily

from twilio.rest import Client

from viam.logging import getLogger

logger = getLogger(__name__)

class MySensor(Sensor):
    # Subclass the Viam Sensor component and implement the required functions
    MODEL: ClassVar[Model] = Model(ModelFamily("acme","memory_sensor"), "RaspPi")
    auth_token = None
    account_sid = None
    recipient_phone = None
    deliverer_phone = None
    threshold = 1
    
    @classmethod
    def new(cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        sensor = cls(config.name)
        return sensor

    @classmethod
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
        auth_token = config.attributes.fields['auth_token'].string_value
        if auth_token == '':
            logger.warning('no twilio auth_token')
        
        account_sid = config.attributes.fields['account_sid'].string_value
        if account_sid == '':
            logger.warning('no twilio account_sid')
        
        recipient_phone = config.attributes.fields['recipient_phone'].string_value
        if recipient_phone == '':
            logger.warning('no twilio recipient_phone')
        
        deliverer_phone = config.attributes.fields['deliverer_phone'].string_value
        if deliverer_phone == '':
            logger.warning('no twilio deliverer_phone')
        
        threshold = config.attributes.fields['threshold'].string_value
        if threshold == '':
            logger.warning('no alert threshold')

        return []

    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        self.auth_token = config.attributes.fields['auth_token'].string_value
        self.account_sid = config.attributes.fields['account_sid'].string_value
        self.recipient_phone = config.attributes.fields['recipient_phone'].string_value
        self.deliverer_phone = config.attributes.fields['deliverer_phone'].string_value
        self.threshold =  config.attributes.fields['threshold'].string_value

    async def get_readings(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Mapping[str, Any]:
        with open("/proc/meminfo") as memory_info:
            content = memory_info.readlines()

        memory_dict = {}

        for line in content:
            line = line.replace("\n", "").split(":")
            memory_dict[line[0]] = line[1].replace("kB", "").strip()
        memory_allocation = float(memory_dict["MemFree"]) / float(memory_dict["MemAvailable"])

        self.call_twilio(memory_allocation)

        return memory_allocation
    
    def call_twilio(self, sensor_reading):
        if self.auth_token == '' or self.account_sid == '' or self.recipient_phone == '' or self.deliverer_phone == '' or self.threshold == '':
            if sensor_reading > self.threshold:
                client = Client(self.account_sid, self.auth_token)
                message = client.messages.create(
                    from_= self.deliverer_phone,
                    to = self.recipient_phone,
                    body = str(self.name) + " over alert threshold."
                )
        else:
            logger.warn("Missing Twilio Attributes...")


# Anything below this line is optional, but may come in handy for debugging and testing.
# To use, call `python wifi_sensor.py` in the command line while in the `src` directory.
async def main():
    memory=MySensor(name="memory")
    signal = await memory.get_readings()
    print(signal)

if __name__ == '__main__':
    asyncio.run(main())