include .env

help:
	@echo "++   PROJECT COMMANDS"
	@echo "++ 	make build run"
	@echo "++ 	make stop clean"
	@echo "++ 	make camera_connected"
	@echo "++ jetson: v4l2-ctl --list-devices"

################################
# DOCKER COMMANDS
build:
	docker buildx build -t oakd_base .docker -f .docker/base.Dockerfile
	docker buildx build -t $(IMAGE_NAME) .docker --build-arg SUPERVISORD_CONF=$(SUPERVISORD_CONF)

run:
	xhost + || continue
	docker run -d --name $(CONTAINER_NAME) \
	    --privileged \
	    --net=host \
	    --device /dev/snd \
	    -v /etc/localtime:/etc/localtime:ro \
	    $(AUDIO_BIND) \
	    $(X11_BIND) \
	    $(MEDIA_VOLUME) \
	    $(OAKD_CONFIG) \
	    -v $(shell pwd)/gstreamer/src:/gstreamer/src:ro \
	    -v $(shell pwd)/gstreamer/common_utils:/gstreamer/common_utils:ro \
	    -v $(shell pwd)/gstreamer/__init__.py:/gstreamer/__init__.py:ro \
	    -v $(shell pwd)/gstreamer/logs:/gstreamer/logs \
	    -w /gstreamer \
	    -e DISPLAY=$(DISPLAY) \
	    $(IMAGE_NAME)

################################
## project commands
enter:
	docker exec -it $(CONTAINER_NAME) bash
stop:
	docker kill $(CONTAINER_NAME)
clean:
	docker network prune && docker container prune && docker volume prune

################################
# LINTING
lint:
	@echo "++ Linting codebase"
	docker exec -it $(CONTAINER_NAME) bash -c "flake8 /gstreamer"

################################
# HELPERS
camera_connected:
	lsusb | grep MyriadX
test_gst:
	docker exec -it $(CONTAINER_NAME) \
	 bash -c "gst-launch-1.0 -e videotestsrc pattern=snow ! video/x-raw,width=1280,height=720 ! autovideosink"
view_config:
	@echo "Configs are located here: gstreamer/src/conf.py"
	@echo "cat gstreamer/src/conf.py"
file_permissions:
	chown -R ${USER}:${USER} *
	chmod -R 775 *
clean_git:
	sudo find . | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | sudo xargs rm -rf
	git repack -a -d --depth=250 --window=250
	git fetch --prune
