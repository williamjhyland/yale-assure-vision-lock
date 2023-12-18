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

More info here: https://python-kasa.readthedocs.io/en/latest/cli.html#discovery

Supported Plugs:
HS100
HS103
HS105
HS107
HS110
KP100
KP105
KP115
KP125
KP401
EP10
