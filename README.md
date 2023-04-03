![python](https://img.shields.io/badge/python-3.8-blue)
![gstreamer](https://img.shields.io/badge/gstreamer-1.16-purple)

# VMS-mini

- VMS for raddog

------
------

# Table of contents
1. [tl-dr](#configuration)
2. [local-server](#local-server)
3. [remote-server](#remote-server)
4. [app-configs](#app-configs)



# TL-DR


__connect to bench setup__


- a NUC has teamviewer on it
- from the NUC you can SSH into the Jetson

```bash
NUC
teamviewer: 855912318
password: radsw_21_NUC
username: nuc
password: radsw_21_NUC

Jetson
ssh: ssh orin5@192.168.123.17
password: radsw_21_ORIN5
```

__project_location__

```bash
cd ~/vms/vms-mini
```


- all you need is the `Makefile` and `gstreamer/src/app_config/conf.py` to get going


- build and run docker container
```bash

make build
make run

```

- run the application

```bash
# view the config files (go to this path and change configs if neccessary)
make view_config

# run the application 
make run_vms

```

- useful commands

```bash
# view all available commands
make help

# test gstreamer is working
make test_gst

# probe cameras
make camera_connected

# kill docker container
make stop
# clean up docker containers
make clean

# docker exec into the container
make enter
# clean up
make clean

```

# Local Server

- test that you can connect and pull a video stream from the RTMP server (IF YOU ARE ON THE SAME NETWORK as Jetson Orin)
- install gstreamer so you can run the command below  (run gstreamer/docker/amd64/scripts/install_gst.sh on device)

```bash
# with display connected to the device
gst-play-1.0 -v rtmp://192.168.121.17:1935/live/stream_rtmp_cam1
# without display connected to the device
GST_DEBUG=4 gst-launch-1.0 -e rtmpsrc location=rtmp://192.168.123.17:1935/live/stream_rtmp_cam1 ! fakesink dump=true
```

# Remote Server

- view REMOTE SERVER accepting streams (put this link in your web browser)
- navigate to WebRTCEE app (https://radm.co:5443/#/applications/WebRTCAppEE)

```bash
https://radm.co:5443
username: vms@vms
password: k8bwP334jGu9TUK
```



# app-configs

- refer to gstreamer/README.md for details on configuring the app
- refer to Makefile for quick commands to build, start, and run the project
- to make this work on a Jetson Orin, you should only have to run the commands above in #TL-DR
- to make this work on your laptop with a USB camera, checkout this branch `v1.0_laptop` (only the configs have changed)

---

- fin!
