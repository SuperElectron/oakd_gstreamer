# Configs

__payload.json__

- The expected payload format that the dashboard will receive

__conf.py__

- LABEL_MAP is a list of labels for the NN you want to run

- shared variables between `camera` and `gst` are included below and must match for the gst pipeline to run properly

```bash
CAM_WIDTH = 1920
CAM_HEIGHT = 1080
PIPELINE_FPS = "30"
COLOR_ORDER = "BGR"
```

- `AppConfig` this sets configs for each class in gstreamer/src/camera
```json

CAM_WIDTH = 1920
CAM_HEIGHT = 1080
PIPELINE_FPS = "30"
COLOR_ORDER = "BGR"

ip_cameras = {                      // for connection=POE: put IP address of capture_av here.  (note: can use mxid from USB cam and this works!)
    "cam1": "192.168.120.20"
}

APP_CONFIG = {
  "camera": {                       // Camera pipeline (CameraPipeline.py)
    "camera_caps": {                  // sets the dai.node.ColorCamera configs
      "resolution": "1080p",        
      "color_order": COLOR_ORDER,   
      "fps": PIPELINE_FPS           
    },
    "frame_nn": {
      "width": 300,                   // sets the 'preview' size for (dai.node.ColorCamera) -> detector
      "height": 300
    },
    "frame_resize": {
      "width": CAM_WIDTH,             // sets the resize frame size sending to gstreamer pipeline
      "height": CAM_HEIGHT
    },
    "model": {                     // nn configurations
      "path": "/device_media/oakd/mobilenet-ssd_openvino_2021.4_6shave.blob",
      "threshold": 0.5
    },
    "tracker": {                  // sets dai.node.ObjectTracker parameters and post processing
      "classes": [15],                  // refer to LABEL_MAP below for which objects will be tracked
      "type": "histogram",              // tracker algorithm options (histogram, zeroterm_imageless, shortterm_imageless, shortterm_kcf)
      "identifier": "unique_id",        // tracking id identifier algorithm (smallest_id, unique_id)
      "id_interval": 120,               // send payload for tracking id every multiple of this
      "min_frames": 10                  // send payload for tracking id after this number of frames tracked
    },
    "store_img_enabled": True,          // save images locally (gstreamer/logs/images)
    "osd_write": True,                  // write bbox and info onto the frame
    "azure_enabled": False,             // send images to azure when detections are made
    "http_enabled": False,              // send payload to dashboard api when detections are made
    "gst_enabled": True,                // spin up video streaming pipeline
    "dump_enabled": True,               // save detection payloads to local folder (gstreamer/logs/payload)
    "connection": "poe",                // connection type to capture_av (usb, or poe)
    "timezone": "Canada/Eastern"     // local timezone for creating capture timestamp (Canada/Eastern, Canada/Pacific)
  },
  "gst": {                              // video streaming pipeline (AppSrcPipeline.py)
    "pipeline": {                       // pipeline options (display, file, server, rtmp)
      "remote": "display",                // display = pop up video; file = save to file;
      "local": "rtmp"                     // server = remote server for WebRTC); RTMP= local server (docker IP address)
    },
    "remote_url": "rtmp://radm.co/WebRTCAppEE/raddog",  // [REMOTE SERVER] rtmp url of remote server (Ant Media Server)
    "local_url": "rtmp://0.0.0.0:1935/live/stream",     // [LOCAL SERVER]  rtmp url for Odroid app
    "video_location": "/gstreamer/logs/video",          // location where the video is stored is you use pipeline['remote'] = "file"
    "src": {                      // Appsrc caps to ingest video stream
      "caps": {                         // expected configs that capture_av pipeline is using
        "fps": PIPELINE_FPS,            
        "frame_width": CAM_WIDTH,       
        "frame_height": CAM_HEIGHT,     
        "color_order": COLOR_ORDER
      },
      "properties": "do-timestamp=true is-live=true emit-signals=true format=GST_FORMAT_TIME"
    },
    "src_names": ip_cameras,       // names of cameras that will be streamed
  },
  "azure": {                      // azure configs for sending images to storage blob
    "robot_id": "1584",
    "robot_name": "ross-1",
    "uri": "https://perception.blob.core.windows.net/dashboard-staging-test",
    "security": {
      "account": "perception",
      "container": "test-cassi",
      "key": "7b6ckB9FJDTddkNf83NohtwKvnIPxMTTwvFQ7KXq6rSIBK/78pgzsi0kj46aJDIikqAi9qTKsdXi+AStn6VFWg==",
      "connection_string": "DefaultEndpointsProtocol=https;AccountName=perception;AccountKey=7b6ckB9FJDTddkNf83NohtwKvnIPxMTTwvFQ7KXq6rSIBK/78pgzsi0kj46aJDIikqAi9qTKsdXi+AStn6VFWg==;EndpointSuffix=core.windows.net"
    }
  },
  "http": {                  // Http info for sending payloads to dashboard backend
    "uri": "https://rad-staging.azurewebsites.net/umbraco/api/RobotDetails/PostNJRobotCameraDetails"
  }
}

```