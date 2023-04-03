#!/usr/bin/env python3

import logging
from gstreamer.common_utils.setup_logging import setup_logging
from gstreamer.src.capture_av.Camera import CaptureAV
from gstreamer.src.conf import AppConfig as Conf
from gstreamer.src.client.rtsp_client import RtspClient


if __name__ == "__main__":
    from time import sleep
    logger = logging.getLogger(__name__)
    setup_logging()
    logging.info(f"{__file__} Starting script")
    server = CaptureAV(Conf)
    client = RtspClient(Conf["rtsp_client"])

    try:
        if Conf['capture_av']['gst_enabled']:
            server.gst_app.thread.start()
            while not server.run_flag:
                sleep(0.1)
            server.thread.start()
        client.run()

    except Exception as runTimeError:
        logger.error(f"{__file__} Runtime Error: {runTimeError}")
    finally:
        if Conf['capture_av']['gst_enabled']:
            server.gst_app.thread.join()
            logger.info(f"{__file__} Gst pipeline joined ")

        server.thread.join()
        client.run_flag = False
        logger.info(f"{__file__} capture_av pipeline joined ")

    logger.info(f"{__file__} FINISHED")
