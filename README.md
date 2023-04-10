
![python](https://img.shields.io/badge/python-3.8-blue) 

![gstreamer](https://img.shields.io/badge/gstreamer-1.16-purple)

![oakdLite](https://img.shields.io/badge/depthaiSDK-2.0.0-green)
![oak-D](https://img.shields.io/badge/oak_D-1.0-red)


---

# Oakd-Gstreamer

- Connect to OakD camera and link to gstreamer pipeline to create a RTMP server from which external clients can stream

---


# Table of contents
1. [tl-dr](#tl-dr)
2. [client connection](#client-connection)
3. [app-configs](#app-configs)


# TL-DR

- all you need is the `Makefile` and `gstreamer/src/app_config/conf.py` to get going
- here we assume that the IP address of the device is `192.168.121.17` (update/change `SERVER` in `gstreamer/src/conf.py`)

__getting_started__

- build and run docker container
```bash
# docker build
make build
# docker run
make run
# view the config files (go to this path and change configs if necessary)
make view_config
```

---

# client connection

- test that you can connect and pull a video stream from the RTMP server (IF YOU ARE ON THE SAME NETWORK as Jetson)
- install gstreamer, so you can run the command below  (run `.docker/scripts/install_gst.sh` on your device)
- here we assume that the IP address of the device is `192.168.121.17` (update/change it in `gstreamer/src/conf.py`)
```bash
# with display connected to the device
gst-play-1.0 -v rtmp://192.168.121.17:1935/live/stream_rtmp_cam1
# without display connected to the device
GST_DEBUG=4 gst-launch-1.0 -e rtmpsrc location=rtmp://192.168.123.17:1935/live/stream_rtmp_cam1 ! fakesink dump=true
```

---


# app-configs

- refer to `gstreamer/README.md` for details on configuring the app
- refer to Makefile for quick commands to build, start, and run the project
- to make this work on a Jetson (Orin or Xavier), you should only have to run the commands above in #TL-DR

---

- fin!
