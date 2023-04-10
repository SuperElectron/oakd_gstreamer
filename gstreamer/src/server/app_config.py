
"""
CONFIGS:
- view the README.md in this directory
"""

CAM_WIDTH = 1920
CAM_HEIGHT = 1080
PIPELINE_FPS = "30"
COLOR_ORDER = "BGR"

ip_cameras = {
    "camera1": "19443010F1A1EE1200",
    "camera2": "192.168.122.21",
    "camera3": "192.168.122.22",
}
SERVER_IP="192.168.1.69"

rtsp_config = {
    "ip_address": SERVER_IP,
    "port": "8554",
    "pipeline_conf": [
        {
            "name": "camera1",
            "fps": 30,
            "width": 1920,
            "height": 1080,
            "source": {
                "type": "oakd"
            },
            "extension": "/camera1"
        },
        {
            "name": "camera2",
            "fps": 30,
            "width": 1920,
            "height": 1080,
            "source": {
                "type": "file",
                "location": "/gstreamer/sample_1080p_h264.mp4"
            },
            "extension": "/camera2"
        }
    ]
}

AppConfig = {
    "camera": {
        "camera_caps": {
            "resolution": "1080p",
            "color_order": COLOR_ORDER,
            "fps": PIPELINE_FPS,
        },
        "frame_resize": {
            "width": CAM_WIDTH,
            "height": CAM_HEIGHT,
        },
        "cameras": ip_cameras,
        "store_img_enabled": False,
        "gst_enabled": True,
        "connection": "poe",
        "timezone": "Canada/Eastern",
    },
    "rtsp": rtsp_config
}