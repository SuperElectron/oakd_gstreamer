#!/bin/bash

# Example usage: ./install_gst.sh

export WORKDIR="/start/scripts"
export NAME="[install_gst.sh]: "
echo "${NAME} STARTING "

# Bash failure reporting for the script
set -eE -o functrace
failure() {
  local lineno=$1
  local msg=$2
  echo "${NAME} Failed at $lineno: $msg"
}
trap '${NAME} failure ${LINENO} "$BASH_COMMAND"' ERR

echo "${NAME} pre-flight check for exiting folder $WORKDIR from docker COPY "
INSTALL_DIR_EXISTS="$(test -d $WORKDIR && echo 'yes' || echo 'no')"
if [[ "$INSTALL_DIR_EXISTS" == "no" ]]; then
  echo "--(fail)-- install directory exists: ${WORKDIR}"
  exit 1;
else
  echo "--(pass)-- install directory exists: ${WORKDIR}"
fi

echo "${NAME} Installing python 3 and deps for gstreamer"
apt-get update -y -qq
apt-get install -y -qq \
  python3-gi \
  libgirepository1.0-dev \
  libcairo2-dev \
  gir1.2-gstreamer-1.0 \
  gstreamer-1.0 \
  gstreamer1.0-dev \
  gstreamer1.0-plugins-base-apps

echo "${NAME} Setting up python bindings for gstreamer "
python3 -m pip install pycairo --
python3 -m pip install PyGObject --

echo "${NAME} Installing apt packages: gstreamer "
apt-get install -y -qq \
    graphviz \
    python3-gst-1.0 \
    gir1.2-gst-rtsp-server-1.0 \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-doc \
    gstreamer1.0-tools \
    gstreamer1.0-x \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 \
    gstreamer1.0-pulseaudio \
    libgstreamer-plugins-good1.0-0 \
    libgstreamer-plugins-good1.0-dev \
    gstreamer1.0-plugins-good \
    gstreamer1.0-rtsp

echo "${NAME} Installing python packages "
python3 -m pip install --upgrade wheel pip setuptools --
python3 -m pip install git+https://github.com/jackersson/gstreamer-python.git
python3 -m pip install -r $WORKDIR/requirements.txt --

echo "${NAME} FINISHED "
