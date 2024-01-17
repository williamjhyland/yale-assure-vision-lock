# wifi-sensor/src/__init__.py
from viam.components.sensor import Sensor
from viam.resource.registry import Registry, ResourceCreatorRegistration
from .yale_assure_2 import MySensor


# Registry.register_resource_creator(Sensor.SUBTYPE, MySensor.MODEL, ResourceCreatorRegistration(MySensor.new))