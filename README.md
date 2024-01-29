# Yale Assure 2 Smart Lock

This example uses *facial-detector* which is is a Viam modular vision service that uses the [DeepFace](https://github.com/serengil/deepface) library to perform facial detections. More information here: https://github.com/viam-labs/facial-detection
Provide a vision service, a relevant tag, a camera, and a camera name. The lock will unlock or remain locked depending on if a detection with the given confidence interval is found.

# A Note About Authentication
The Yale Lock requires an access token in order to authenticate. I've included an auth.py script to authenticate against your profile. Upon running this script you will be prompted to enter in a verification code. Successful authentication will generate an "accesstoken.json" file which needs to be made accessible to the main script.

# Configuration
Attribute Guide:
```json
{
  "access_token_path": "YOUR ACCESS TOKEN PATH", 
  "source_camera": "YOUR CAMERA HERE",
  "tags": {
    "YOUR LABEL HERE": "YOUR CONFIDENCE INTERVAL HERE"
  },
  "vision_service": "YOUR SERVICE HERE",
  "lock_name": "YOUR LOCK NAME HERE"
}
```

Example Config:
```json
{
  "access_token_path": "/home/viam/yale-assure-vision-lock/accesstoken.json", 
  "source_camera": "webcam",
  "tags": {
    "Bill": 0.3
  },
  "vision_service": "face-detector-vision",
  "lock_name": "Bills Lock"
}
```

# Required Dependencies
```json
  "depends_on": [
    "webcam",
    "detection-camera",
    "face-detector-vision"
    ]
```

  The Module will not start up without the dependencies set.


## Some (Not all) Important Prerequisites for *facial-detector*...

``` bash
sudo apt update && sudo apt upgrade -y
sudo apt-get update && sudo apt-get install ffmpeg libsm6 libxext6  -y
```
Note: if using this method, any cameras you are using must be set in the `depends_on` array for the service configuration, for example:

```json
      "depends_on": [
        "webcam"
      ]
```

More info here: 
https://github.com/bdraco/yalexs
https://github.com/viam-labs/facial-detection
