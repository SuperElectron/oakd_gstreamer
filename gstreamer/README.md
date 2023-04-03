![python](https://img.shields.io/badge/python-3.8-blue)
![gstreamer](https://img.shields.io/badge/gstreamer-1.16-purple)

# VMS-mini

- VMS for raddog

------
------

# Table of contents
1. [Introduction](#introduction)
2. [Configuration](#configuration)
3. [Modules Inside Project](#modules-inside-project)



# Introduction

- Mini VMS that connects to OAKD camera and takes video + tracker stream and connects to external clients
- external clients
    - remote server = Ant Media Server
    - local server = RTMP server for Adroid board
    - Azure = detection images 
    - HTTP = dashboard backend API for detection payload



# Configuration

- refer to `gstreamer/src/app_config/conf.py` and `gstreamer/src/app_config/README.md`

- logging into the device: [jetson-login](https://radtracker.atlassian.net/wiki/spaces/RADDOG/pages/1870364710/Connecting+to+Remote+Desk+with+NUC+Jetson+ORINhttps://radtracker.atlassian.net/wiki/spaces/RADDOG/pages/1870364710/Connecting+to+Remote+Desk+with+NUC+Jetson+ORIN)


# Modules Inside Project

- app_config, camera, and dev are the 3 main modules
- the main program is locaated in `gstreamer/src/camera/main.py`
- you can run each individual class in `gstreamer/src/camera` by doing `python3 class.py` where class.py is the file you want to run


```bash
├── app_config                   // configs for each class in capture_av module
│   ├── conf.py
│   ├── __init__.py
│   ├── payload.json
│   └── README-appConfig.md
├── capture_av                      // main project module
│   ├── AppSrcPipeline.py           // Gstreamer pipeline that sends stream to remote server and local server
│   ├── AzureClient.py              // posting images to azure
│   ├── CameraPipeline.py           // depth ai pipeline to get video and metadata from the capture_av
│   ├── HttpClient.py               // post detection results to dashboard backend api
│   ├── __init__.py
│   └── main.py                     // MAIN program to run
├── server                         // test repos for debugging
│   ├── test_oakd_camera_connection.py               // change IP address on line 9 to connect to a POE capture_av
│   ├── va_test.py                  // gstreamer pipeline to connect to webcam and audio
│   └── v_test.py                   // gstreamer pipeline to connect with webcam
└── __init__.py

```

---

- fin!
