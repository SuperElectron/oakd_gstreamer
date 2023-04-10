#!/bin/bash

# Install depthai
# Example usage: ./install_depthai.sh
export NAME="[install_depthai.sh] "

set -eE -o functrace
failure() {
  local lineno=$1
  local msg=$2
  echo "${NAME} Failed at $lineno: $msg"
}
trap '${NAME} failure ${LINENO} "$BASH_COMMAND"' ERR

echo "${NAME} STARTING ";

echo "${NAME} Starting installation scripts for OAKD"
apt-get update -yqq;
apt-get install -y libopencv-dev
cd /start && git clone https://github.com/luxonis/depthai.git
cd /start/depthai && python3 -m pip install -r requirements.txt

echo "${NAME} Setting udev rules for usb"
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | tee /etc/udev/rules.d/80-movidius.rules

echo "${NAME} FINISHIED"
