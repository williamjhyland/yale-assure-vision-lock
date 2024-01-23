# Yale Assure 2 Smart Lock

Provide a vision service, a relevant tag, a camera, and a camera name. The lock will lock or unlock depending on if the approved person's face is seen or not.

Example Config:

{
  "source_camera": "webcam",
  "tags": {
    "Bill": 0.3
  },
  "vision_service": "face-detector-vision",
  "lock_name": "Bills Lock"
}

# Required Dependencies
  "depends_on": [
    "webcam",
    "detection-camera",
    "face-detector-vision"
    ]

  The Module will not start up without the dependencies set.

Run "Kasa Discover" from python to find your Kasa Device

More info here: 
https://github.com/bdraco/yalexs
https://github.com/viam-labs/facial-detection
