import depthai as dai
from threading import Thread
import logging
import cv2
from pprint import pprint
import contextlib
from time import sleep
from gstreamer.src.server.rtsp_server import GstServer

logger = logging.getLogger(__name__)
logging.getLogger(__name__).setLevel(logging.WARNING)


class CameraPipeline(object):
    def __init__(self, conf):

        assert conf is not None
        assert conf["camera"] is not None
        # Flag to keep thread running continuously
        self.run_flag = True
        # Camera output queues to pass data to gstreamer thread
        self.pipeline = []
        self.q_dict = {}
        # Class configs
        self.conf = None
        self.camera_count = 0

        # Load configs, instantiate gstreamer App & OakD camera app
        self.set_configs(conf['camera'])

        # Main Thread objects
        self.gst_app = GstServer(conf['rtsp'])
        self.thread = Thread(target=self.run, daemon=True)

    def set_configs(self, conf):
        _log_prefix = "[set_configs]\n-- "
        logger.info(f"{_log_prefix}\n-- CONFIGS: ")
        pprint(conf)

        assert isinstance(conf['camera_caps'], dict)
        for key, value in conf['camera_caps'].items():
            assert isinstance(key, str)
            assert isinstance(value, str)

        assert isinstance(conf['frame_resize'], dict)
        for key, value in conf['frame_resize'].items():
            assert isinstance(key, str)
            assert isinstance(value, int)

        assert isinstance(conf['store_img_enabled'], bool)
        assert isinstance(conf['gst_enabled'], bool)

        assert isinstance(conf['connection'], str)
        assert isinstance(conf['timezone'], str)

        self.conf = conf

    def load_cam_resolution(self):
        _log_prefix = "[load_cam_resolution]\n-- "

        code = self.conf['camera_caps']['resolution']
        res = None

        if code.lower() == "1080p":
            res = dai.ColorCameraProperties.SensorResolution.THE_1080_P
        elif code.lower() == "720p":
            res = dai.ColorCameraProperties.SensorResolution.THE_720_P
        elif code.lower() == "800p":
            res = res = dai.ColorCameraProperties.SensorResolution.THE_800_P
        elif code.lower() == "4k":
            res = res = dai.ColorCameraProperties.SensorResolution.THE_4_K
        elif code.lower() == "5mp":
            res = res = dai.ColorCameraProperties.SensorResolution.THE_5_MP
        else:
            logging.error(f"{_log_prefix} Invalid config code passed. Validate string from this function")
            raise RuntimeError
        return res

    def load_cam_color_order(self):
        _log_prefix = "[load_cam_color]\n-- "

        code = self.conf['camera_caps']['color_order']
        res = None

        if code.lower() == "rgb":
            res = dai.ColorCameraProperties.ColorOrder.BGR
        elif code.lower() == "bgr":
            res = dai.ColorCameraProperties.ColorOrder.BGR
        else:
            logging.error(f"{_log_prefix} Invalid config code passed. Validate string from this function")
            raise RuntimeError
        return res

    @staticmethod
    def load_camera_state(code):
        _log_prefix = "[load_camera_state]\n-- "
        state = ""
        if int(code) == 0:
            state = "idle"
        elif int(code) == 1:
            state = "connected"
        elif int(code) == 2:
            state = "available"
        else:
            logging.warning(f"{_log_prefix} Unknown camera state (code={code})")
            raise RuntimeError
        return state

    def create_pipeline(self):
        _log_prefix = "[create_pipeline]\n-- "
        logger.info(f"{_log_prefix} Creating pipeline")

        p = dai.Pipeline()

        """ Define sources and sinks """
        # define sources for video stream
        video_in = p.create(dai.node.ColorCamera)

        # define outputs for queue extraction via device.getOutputQueue(<name>)
        video_out = p.createXLinkOut()

        """ Set properties """
        # Set properties for camera video component
        # video_in.setPreviewSize(self.conf['frame_nn']['width'], self.conf['frame_nn']['height'])
        video_in.setBoardSocket(dai.CameraBoardSocket.RGB)
        video_in.setInterleaved(False)
        video_in.setFps(int(self.conf["camera_caps"]["fps"]))
        video_in.setResolution(self.load_cam_resolution())
        video_in.setColorOrder(self.load_cam_color_order())

        # Set queue extraction <name>, extract with q = `device.getOutputQueue(<name>)`
        video_out.setStreamName("video")

        """ Linking """
        video_in.video.link(video_out.input)

        """ Property check """
        logger.info(f"{_log_prefix} CAMERA \n"
                    f"\tfps=({video_in.getFps()})\n"
                    f"\tresolution=({video_in.getResolution()})\n"
                    f"\tcolorOrder=({video_in.getColorOrder()})\n"
                    f"\twidth=({video_in.getStillWidth()})\n"
                    f"\theight=({video_in.getStillHeight()})"
                    )
        # Catch errors where FPS is not possible
        if int(video_in.getFps()) != int(self.conf['camera_caps']['fps']):
            logger.debug(f"{_log_prefix} Cannot run camera at this fps\n"
                         f"\tGiven FPS ({self.conf['camera_caps']['fps']})\n"
                         f"\tDevice FPS ({video_in.getFps()})")
            raise RuntimeError

        return p

    def send_frames(self, stream_id, img, seq_num):
        _log_prefix = "[send_frames]\n-- "

        resized = cv2.resize(img, (self.conf['frame_resize']['width'], self.conf['frame_resize']['height']),
                             interpolation=cv2.INTER_AREA)

        if self.conf['gst_enabled']:
            logging.info(f"Sending video frame to stream: {stream_id}")
            if stream_id == "camera1":
                self.gst_app.pipelines[0].push(frame=resized, src_name=stream_id)
                logging.debug("Sending frame to camera1")
            elif stream_id == "camera2":
                self.gst_app.pipelines[1].push(frame=resized, src_name=stream_id)
                logging.debug("Sending frame to camera2")
            elif stream_id == "camera3":
                self.gst_app.pipelines[2].push(frame=resized, src_name=stream_id)
                logging.debug("Sending frame to camera3")

        if seq_num == 0 or seq_num % 3600 == 0:
            logger.info(f"{_log_prefix} src=({stream_id}) count=({seq_num})")

    def unpack_queue(self, stream_id, queue):
        _log_prefix = "[unpack_queue]\n --"

        img = None
        payload = None
        frame_width = None
        frame_height = None

        video = queue['video'].get()

        if video is not None:
            # logging.debug(f"{_log_prefix} Got an image (v_counter = {video.getSequenceNum()})")
            img = video.getCvFrame()
            frame_width = img.shape[0]
            frame_height = img.shape[1]
            f_n = video.getSequenceNum()
            cv2.putText(img, f"frame({f_n})", (2, frame_height - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, (255, 255, 255))

        # If the frame is available, send to gstreamer pipeline and azure
        if img is not None:
            self.send_frames(stream_id, img, video.getSequenceNum())

    def run(self):
        _log_prefix = '[run]\n-- '
        logger.info(f"{_log_prefix} Starting thread")

        with contextlib.ExitStack() as stack:
            deviceInfos = dai.Device.getAllAvailableDevices()
            usbSpeed = dai.UsbSpeed.SUPER
            openVinoVersion = dai.OpenVINO.Version.VERSION_2021_4

            devices = []
            counter = 0
            for deviceInfo in deviceInfos:
                deviceInfo: dai.DeviceInfo
                device: dai.Device = stack.enter_context(dai.Device(openVinoVersion, deviceInfo, usbSpeed))
                devices.append(device)
                print("===Connected to ", deviceInfo.getMxId())
                mxId = device.getMxId()
                cameras = device.getConnectedCameras()
                usbSpeed = device.getUsbSpeed()
                eepromData = device.readCalibration2().getEepromData()
                print("   >>> MXID:", mxId)
                print("   >>> Num of cameras:", len(cameras))
                print("   >>> USB speed:", usbSpeed)
                print("   >>> IPAddress:", deviceInfo.name)
                if eepromData.boardName != "":
                    print("   >>> Board name:", eepromData.boardName)
                if eepromData.productName != "":
                    print("   >>> Product name:", eepromData.productName)
                counter += 1
                name = "camera" + str(counter)
                device.startPipeline(self.create_pipeline())

                self.q_dict[name] = {
                    "video": device.getOutputQueue(name="video", maxSize=2, blocking=False),
                }
                logger.info(f"{_log_prefix} Added camera pipeline for device (ipAdress={deviceInfo.name}, id={mxId})")

            while self.run_flag:
                for stream_id, queue in self.q_dict.items():
                    try:
                        logging.info(f"received {stream_id}")
                        self.unpack_queue(stream_id, queue)

                    except Exception as ThreadError:
                        logging.error(f"{_log_prefix} Camera pipeline error [stream_id=({stream_id})]: {ThreadError}")
                        self.run_flag = False

        # Send commands to kill the other threads
        if self.conf['gst_enabled']:
            self.gst_app.run_flag = False


if __name__ == "__main__":
    from gstreamer.src.server.app_config import AppConfig
    from gstreamer.common_utils.setup_logging import setup_logging

    setup_logging(folder="/gstreamer/logs", filename="camera.log")
    logger.info(f" STARTING")
    app = CameraPipeline(AppConfig)
    logger.info(f" Starting application thread ")

    try:
        if AppConfig['camera']['gst_enabled']:
            app.gst_app.thread.start()
            sleep(2)
        app.thread.start()

    except Exception as runTimeError:
        logger.error(f" Runtime Error: {runTimeError}")

    finally:
        if AppConfig['camera']['gst_enabled']:
            app.gst_app.thread.join()
            logger.info(f" Gst pipeline joined ")

        app.thread.join()
        logger.info(f" camera pipeline joined ")

    logger.info(f" FINISHED")
