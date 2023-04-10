
CAM_WIDTH = 1920
CAM_HEIGHT = 1080
PIPELINE_FPS = "30"
COLOR_ORDER = "BGR"

oakd_cameras = {
    "camera1": "19443010F1A1EE1200"
}

SERVER="192.168.1.69"

rtsp_server_config = {
    "ip_address": SERVER,
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
        }
    ]
}

rtsp_client_config = {
    "url": f"rtsp://{SERVER}:8554/camera1"
}

AppConfig = {
    "capture_av": {
        "camera_caps": {
            "resolution": "1080p",
            "color_order": COLOR_ORDER,
            "fps": PIPELINE_FPS,
        },
        "frame_resize": {
            "width": CAM_WIDTH,
            "height": CAM_HEIGHT,
        },
        "cameras": oakd_cameras,
        "store_img_enabled": False,
        "gst_enabled": True,
        "connection": "poe",
        "timezone": "Canada/Eastern",
    },
    "client": rtsp_server_config,
    "rtsp_client": rtsp_client_config
}


