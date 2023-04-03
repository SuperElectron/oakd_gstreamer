include .env

# HELPERS
help:
	@echo "++   PROJECT COMMANDS"
	@echo "++ 	make build"
	@echo "++ 	make run"
	@echo "++ jetson: v4l2-ctl --list-devices"

# FILE PERMISSIONS (root-> $USER)
file_permissions:
	chown -R ${USER}:${USER} *
	chmod -R 775 *

ssh_key_generate:
	cd ~/.ssh; ssh-keygen

ssh_load:
	eval "$(shell ssh-agent -s)"
	ssh-add ~/.ssh/vms_mini

clean_git:
	sudo find . | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | sudo xargs rm -rf
	git repack -a -d --depth=250 --window=250
	git fetch --prune

################################
# DOCKER COMMANDS

build:
	docker buildx build -t vms_tiny_base .docker/gstreamer -f .docker/gstreamer/base.Dockerfile
	docker buildx build -t $(IMAGE_NAME) .docker/gstreamer --build-arg SUPERVISORD_CONF=$(SUPERVISORD_CONF)

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

test_gst:
	docker exec -it $(CONTAINER_NAME) \
	 bash -c "gst-launch-1.0 -e videotestsrc pattern=snow ! video/x-raw,width=1280,height=720 ! autovideosink"

################################
## project commands
view_config:
	@echo "Configs are located here: gstreamer/src/conf.py"
	@echo "cat gstreamer/src/conf.py"

run_vms:
	docker exec -it $(CONTAINER_NAME) python3 /gstreamer/src/run.py
enter:
	docker exec -it $(CONTAINER_NAME) bash
stop:
	docker kill $(CONTAINER_NAME)
clean:
	docker network prune && docker container prune && docker volume prune
stop_clean: stop clean

################################
# LINTING
lint:
	@echo "++ Linting codebase"
	docker exec -it $(CONTAINER_NAME) bash -c "flake8 /gstreamer"

################################
# TESTING
test_docker:
	docker exec -it $(CONTAINER_NAME) bash -c "python3 -m unittest discover -s /kafka/test -vvv"

################################
# CAMERA
camera_connected:
	lsusb | grep MyriadX
camera_usb:
	@echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/80-movidius.rules
	sudo udevadm control --reload-rules && sudo udevadm trigger
