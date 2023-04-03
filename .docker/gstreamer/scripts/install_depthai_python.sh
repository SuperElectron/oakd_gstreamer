#!/bin/bash

# Install depthai-python
# Example usage: ./install_depthai_python.sh
export NAME="[install_depthai_python.sh] "

set -eE -o functrace
failure() {
  local lineno=$1
  local msg=$2
  echo "${NAME} Failed at $lineno: $msg"
}
trap '${NAME} failure ${LINENO} "$BASH_COMMAND"' ERR

echo "${NAME} STARTING ";

echo "${NAME} Installing depthai-python deps"
apt-get install -yqq \
  curl zip unzip tar git \
  make cmake g++ build-essential pkg-config

echo "${NAME} Clone and build depthai-python repo"
cd /start && git clone https://github.com/luxonis/depthai-python.git
cd /start/depthai-python; git submodule update --init --recursive
#cd /start/depthai-python; python3 examples/install_requirements.py
cd /start/depthai-python; python3 -m pip install .

echo "${NAME} FINISHIED"
