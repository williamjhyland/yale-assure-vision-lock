# Yale Assure 2 Smart Lock

This example uses *facial-detector* which is is a Viam modular vision service that uses the [DeepFace](https://github.com/serengil/deepface) library to perform facial detections. More information here: https://github.com/viam-labs/facial-detection

## Prerequisites for *facial-detector*

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

## Viam Service Configuration

The following attributes may be configured as facial-detector config attributes.
For example: the following configuration would use the `ssd` framework:

``` json
{
  "detection_framework": "ssd"
}
```

### detection_framework

*enum - "opencv"|"retinaface"|"mtcnn"|"ssd"|"dlib"|"mediapipe"|"yolov8" (default: "ssd")*

The detection framework to use for facial detection.  `ssd` is chosen as the default for a good balance of speed and accuracy.

### recognition_model

*enum -   "VGG-Face"|"Facenet"|"Facenet512"|"OpenFace"|"DeepFace"|"DeepID"|"ArcFace"|"Dlib"|"SFace" (default: "ArcFace")*

The model to use for facial recognition.  `ArcFace` is chosen as the default for a good balance of speed and accuracy.

### face_labels

*object*

If configured, expects an object map of key:label, value:path to use in matching against reference face images.
For example:

``` json
{
  "matt": "/path/to/matt.jpg",
  "suzy": "/path/to/suzy_photo.jpg"
}
```

If the input image from get_detections() or get_detections_from_camera() verifies as a match of one of the images specified in the *face_labels* paths, the associated label will be returned.

### verify_threshold

*number(default:.8)*

If [disable_verify](#disable_verify) is false and [face_labels](#face_labels) are set, if the verification confidence does not match or exceed this threshold, it will return as a normal detected "face".

### disable_detect

*boolean(default:false)*

If [disable_verify](#disable_verify) is false and [face_labels](#face_labels) are set, if disable_detect is false, any faces detected but not verified as matching a label will be labeled as *face*.

### disable_verify

*boolean(default:false)*

If false and [face_labels](#face_labels) are set, will attempt to verify any faces detected.
If you only want verified faces to be labeled, set this to false and [disable_detect](#disable_detect) to true.



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
