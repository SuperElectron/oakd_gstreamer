import cv2
import depthai as dai
from pprint import pprint
import logging
from threading import Thread

logger = logging.getLogger(__name__)

CAMERA_ID = "19443010F1A1EE1200"


class CameraCapture(object):

    def __init__(self, conf):
        assert conf is not None
        assert conf["capture_av"] is not None

        self.conf = None
        # Names of capture_av devices that are discovered via usb or poe connection
        self.camera_ids = {}
        self.set_configs(conf['capture_av'])
        # Create a list of available cameras to use
        self.probe_cameras()
        self.t_camera = Thread(target=self.run, daemon=True)

    def set_configs(self, conf):
        _log_prefix = "[set_configs]\n-- "
        logger.info(f"{_log_prefix}\n-- CONFIGS: ")
        pprint(conf)

        assert isinstance(conf['camera_caps'], dict)
        for key, value in conf['camera_caps'].items():
            assert isinstance(key, str)
            assert isinstance(value, str)

        assert isinstance(conf['frame_nn'], dict)
        for key, value in conf['frame_nn'].items():
            assert isinstance(key, str)
            assert isinstance(value, int)

        assert isinstance(conf['frame_resize'], dict)
        for key, value in conf['frame_resize'].items():
            assert isinstance(key, str)
            assert isinstance(value, int)

        assert isinstance(conf['cameras'], dict)
        for key, value in conf['cameras'].items():
            assert isinstance(key, str)
            assert isinstance(value, str)

        assert isinstance(conf['store_img_enabled'], bool)
        assert isinstance(conf['osd_write'], bool)
        assert isinstance(conf['dump_enabled'], bool)

        assert isinstance(conf['connection'], str)
        assert isinstance(conf['timezone'], str)

        self.conf = conf

    def probe_cameras(self):
        _log_prefix = "[probe_cameras]\n --"

        counter = 0
        for device in dai.Device.getAllAvailableDevices():
            cam_id = device.getMxId()
            self.camera_ids[cam_id] = "available"
        logging.info(f"{_log_prefix} Cameras available: {self.camera_ids}")

    def send_frames(self, stream_id, img, seq_num):
        _log_prefix = "[send_frames]\n-- "

        resized = cv2.resize(img, (self.conf['frame_resize']['width'], self.conf['frame_resize']['height']),
                             interpolation=cv2.INTER_AREA)

        if self.conf['store_img_enabled']:
            filename = f"./logs/images/src{stream_id}_{seq_num}.png"
            cv2.imwrite(filename, img)

        if seq_num == 0 or seq_num % 100 == 0:
            logger.info(f"{_log_prefix} src=({stream_id}) count=({seq_num})")

    def run(self):
        _log_prefix = "[run]\n --"

        pipeline = dai.Pipeline()
        camRgb = pipeline.createColorCamera()
        xoutRgb = pipeline.createXLinkOut()
        xoutRgb.setStreamName("rgb")
        camRgb.preview.link(xoutRgb.input)

        device_info = dai.DeviceInfo(CAMERA_ID)
        # device_info.state = dai.XLinkDeviceState.X_LINK_FLASH_BOOTED

        with dai.Device(pipeline, device_info) as device:
            q = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
            logging.debug(f"{_log_prefix} Reading from the queue")
            while True:
                logging.debug(f"{_log_prefix} Got image")
                video = q.get()
                img = video.getCvFrame()
                f_n = video.getSequenceNum()
                if img is not None:
                    self.send_frames("rgb", img, f_n)


if __name__ == "__main__":
    from gstreamer.src.conf import AppConfig
    from gstreamer.common_utils.setup_logging import setup_logging

    setup_logging(filename="poe_camera.log")
    logger.info(f" STARTING")
    app = CameraCapture(AppConfig)
    try:
        app.t_camera.start()
    except Exception as runTimeError:
        logger.error(f" Runtime Error: {runTimeError}")
    finally:
        app.t_camera.join()
        logger.info(f" capture_av pipeline joined ")
    logger.info(f" FINISHED")
