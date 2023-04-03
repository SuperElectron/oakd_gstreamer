FROM ubuntu:20.04
LABEL maintainer="RAD <matt.m@radskunkworks.com>"

ENV DEBIAN_FRONTEND noninteractive

# Python module path for the root import location
ENV PYTHONPATH /

# Docker exec path for login and bash execution root location (mount application here)
WORKDIR /gstreamer

COPY apt /start/apt
COPY scripts /start/scripts
RUN chmod 755 /start -R
# Base installations for the container
RUN apt-get update -yqq

RUN --mount=type=cache,target=/var/cache/apt apt-get update -yqq --fix-missing && \
    apt-get install -yqq --no-install-recommends \
    $(cat /start/apt/general.pkglist) \
    $(cat /start/apt/gst.pkglist) \
    $(cat /start/apt/supervisord.pkglist)  && \
    rm -rf /var/lib/apt/lists/*

# Supervisord logging directories
RUN mkdir -p /var/lock/apache2 /var/run/apache2 /var/run/sshd /var/log/supervisor
RUN /start/scripts/install.sh
RUN /start/scripts/install_gst.sh
RUN /start/scripts/install_depthai.sh
#RUN python3 -m pip install -r /start/scripts/requirements.txt
#RUN python3 -m pip install pycairo
#RUN python3 -m pip install PyGObject
#RUN python3 -m pip install git+https://github.com/jackersson/gstreamer-python.git
