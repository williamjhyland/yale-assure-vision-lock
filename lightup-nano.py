import asyncio
import os
from kasa import SmartPlug

from viam.robot.client import RobotClient
from viam.rpc.dial import Credentials, DialOptions
from viam.components.camera import Camera
from viam.services.vision import VisionClient


# These must be set, you can get them from your robot's 'CODE SAMPLE' tab
robot_api_key = os.getenv('ROBOT_API_KEY') or ''
robot_api_key_id = os.getenv('ROBOT_API_KEY_ID') or ''
robot_address = os.getenv('ROBOT_ADDRESS') or ''

async def connect():
    opts = RobotClient.Options.with_api_key(
      api_key='lllqc086bb1jln9pqv33pjubwdxr8670',
      api_key_id='66e5cc39-9e31-421d-b25b-efecc43a8b6a'
    )
    return await RobotClient.at_address('dogdetector-nano-main.9qdxxor648.viam.cloud', opts)


async def main():
    robot = await connect()

    effdet_vision = VisionClient.from_robot(robot, "effdet-vision")

    N = 100
      
    #example: plug = SmartPlug('10.1.11.221')
    
    plug = SmartPlug('192.168.10.107')
    await plug.update()
    await plug.turn_off()
    state = "off"
    for i in range(N):
        #make sure that your camera name in the app matches "my-camera"       
        detections = await effdet_vision.get_detections_from_camera("webcam")
        found = False
        for d in detections:
            if d.confidence > 0.6:
                print("I see a " + str(d.class_name))
                if d.class_name.lower() == "dog":
                    print("This is a dog!")
                    found = True
        if found:
            #turn on the smart plug
            await plug.turn_on()
            await plug.update()
            print("turning on")
            state = "on"
            await asyncio.sleep(2)
        else:
            # if on turn off the smart plug
            if state == "on":
                await plug.turn_off()
                await plug.update()
                print("turning off")
                state = "off"
            print("there's nobody here")
            # turn off the smart plug

    await asyncio.sleep(1)
    await robot.close()

if __name__ == '__main__':
    asyncio.run(main())