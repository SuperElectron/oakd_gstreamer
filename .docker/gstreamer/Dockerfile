# syntax = docker/dockerfile:1.2
FROM vms_tiny_base:latest
LABEL maintainer="RAD <matt.m@radskunkworks.com>"

ENV DEBIAN_FRONTEND noninteractive
# Python module path for the root import location
ENV PYTHONPATH /

# path to supervisord configuration file for runtime
ARG SUPERVISORD_CONF

# Docker exec path for login and bash execution root location (mount application here)
WORKDIR /gstreamer

# Base installations for the container
RUN apt-get update -yqq && apt-get install -yqq nginx libnginx-mod-rtmp apt-utils ffmpeg

COPY server/nginx-default.conf /etc/nginx/sites-available/default
COPY server/nginx.conf /etc/nginx/nginx.conf
EXPOSE 80/tcp
EXPOSE 1935/tcp

COPY $SUPERVISORD_CONF /etc/supervisor/conf.d/vms.conf

# Command executed for container spin up (docker run)
CMD ["/usr/sbin/nginx", "-g", "daemon off;"]
#CMD ["/usr/bin/supervisord"]
