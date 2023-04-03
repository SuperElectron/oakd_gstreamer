#!/bin/bash

# Example usage: ./install.sh

export NAME="[install.sh]: "
echo "${NAME} STARTING "

# Bash failure reporting for the script
set -eE -o functrace
failure() {
  local lineno=$1
  local msg=$2
  echo "${NAME} Failed at $lineno: $msg"
}
trap '${NAME} failure ${LINENO} "$BASH_COMMAND"' ERR


echo "${NAME} Installing apt packages: base packages "
apt-get install -y -qq \
    netcat net-tools nmap git software-properties-common \
    autoconf automake libtool v4l-utils \
    pulseaudio-utils alsa-base alsa-utils pulseaudio \
    iputils-ping

echo "${NAME} Installing python 3"
apt-get update -y -qq
apt-get install -y -qq \
  python3 \
  python-dev \
  python3-pip \
  python3-dev

python3 -m pip install -r /start/scripts/requirements.txt
echo "${NAME} Set up container logging "
mkdir -p /logs/python
touch /logs/python/python.log
chmod 777 /logs/python/python.log
ln -sf /dev/stdout /logs/python/python.log --

echo "${NAME} FINISHED "
