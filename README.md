# Kasa Smart Plug

Provide a vision service, a relevant tag, a camera, and an IP Address of the Kasa smart plug the light will turn on or off depending on if the detection is seen or not.

Example Config:

{
  "source_camera": "webcam",
  "tags": {
    "Dog": 0.3
  },
  "vision_service": "effdet-vision",
  "plug_ip": "192.168.10.10"
}

# Required Dependencies
  "depends_on": [
    "webcam",
    "detection-camera",
    "effdet-vision"
    ]

  The Module will not start up without the dependencies set.

Run "Kasa Discover" from python to find your Kasa Device

More info here: https://github.com/bdraco/yalexs