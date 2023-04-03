#!/usr/bin/env python3

import os
import sys
from datetime import datetime
import gi
import logging
from time import sleep

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from gstreamer.common_utils.utils import (save_debug_log, sec_to_hms)

logger = logging.getLogger(__name__)
logging.getLogger(__name__).setLevel(logging.WARNING)


class RtspClient:
    def __init__(self, conf=None):
        self.__my_name = "RtspClient"
        self.run_flag = True
        self.log_path = '/gstreamer/logs'
        logger.info(f"{__file__} Starting pipeline {self.__my_name} ")
        self.runtime_clock = {"start": -1, "stop": -1, "runtime": -1}
        self.frame_counter = 0
        self.rtsp_url = conf["url"]
        self.set_up_pipeline()

    def on_pad_added(self, src, new_pad):
        # handler for the pad-added signal
        video_depay = self.pipeline.get_by_name('video_depay')
        sink_pad = video_depay.get_static_pad("sink")

        logger.info(f"{__file__} Received new pad {new_pad.get_name()} from {src.get_name()}")

        # if our converter is already linked, we have nothing to do here
        if sink_pad.is_linked():
            logger.info(f"{__file__} We are already linked. Ignoring.")
            return

        # check the new pad's type
        new_pad_caps = new_pad.get_current_caps()
        new_pad_struct = new_pad_caps.get_structure(0)
        new_pad_type = new_pad_struct.get_name()

        if not new_pad_type.startswith("application/x-rtp"):
            logger.warning(f"{__file__} It has type {new_pad_type} which is not raw audio. Ignoring.")
            return

        # attempt the link
        ret = new_pad.link(sink_pad)
        if not ret == Gst.PadLinkReturn.OK:
            logger.error(f"{__file__} Type is {new_pad_type} but link failed")
        else:
            logger.info(f"{__file__} Link succeeded (type {new_pad_type})")
        return

    def bus_call(self, bus, message):
        t = message.type
        v_src = self.pipeline.get_by_name('source')

        if t == Gst.MessageType.EOS:
            logger.info(f"{__file__} bus_call: End-of-stream\n")
            self.loop.quit()

        elif t == Gst.MessageType.ELEMENT:
            logger.info(f"ELEMENT_MESSAGE: {message.src.__class__.__name__}")
            if 'GstRTSPSrc' in message.src.__class__.__name__:
                logger.info(f"{__file__} Got a message from GstRTSPSrc")

        elif t == Gst.MessageType.STATE_CHANGED:

            # only log changes when the source changes state
            if v_src == message.src:
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.info(
                    f"{__file__} Pipeline state changed from "
                    f"'{Gst.Element.state_get_name(old_state)}' to '{Gst.Element.state_get_name(new_state)}'"
                )
                try:
                    file_name = self.__my_name + Gst.Element.state_get_name(old_state) + "_" + Gst.Element.state_get_name(new_state)
                    save_debug_log(self.pipeline, file_name=file_name, log_dir=self.log_path)
                except Exception as saveDebugError:
                    logger.warning(f"{__file__} save_debug_log: {saveDebugError}")

        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            logger.warning(f"{__file__} bus_call:\n\tWarning: {err}: {debug}\n")

        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"{__file__} bus_call:\n\tError: {err} ")

            if 'Could not open resource for reading and writing.' in err.__str__() and v_src == message.src:
                logger.warning(f"{__file__} bus_call:\n\tCould not connect to source. Trying again in 5 seconds...")
                sleep(5)
            else:
                self.run_flag = False

            logger.warning(f"{__file__} Terminate the pipeline")
            self.loop.quit()

        return True

    def set_up_pipeline(self):
        Gst.init(None)

        ##################################################################
        # Create pipeline objects to manage pipeline state
        self.loop = GLib.MainLoop()
        self.pipeline = Gst.Pipeline()
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.bus_call)

        if not [self.loop, self.pipeline, self.bus]:
            logger.debug(f"{__file__} Unable to create Pipeline objects: \n"
                          f"loop: {self.loop} \n"
                          f"pipeline: {self.pipeline} \n"
                          f"bus: {self.bus} \n")
            raise RuntimeError

        ##################################################################
        # Create pipeline elements

        logger.debug(f"{__file__} Creating Pipeline ...")
        source = Gst.ElementFactory.make("rtspsrc", "source")
        source.connect("pad-added", self.on_pad_added)
        source.set_property("location", self.rtsp_url)
        video_depay = Gst.ElementFactory.make("rtph264depay", "video_depay")
        video_parse = Gst.ElementFactory.make("h264parse", "video_parse")
        video_decode = Gst.ElementFactory.make("avdec_h264", "video_decode")
        sink = Gst.ElementFactory.make("xvimagesink", "video_sink")

        ##################################################################
        # Add elements to pipeline bin

        logger.debug(f"{__file__} Adding elements to Pipeline ...")
        self.pipeline.add(source)
        self.pipeline.add(video_depay)
        self.pipeline.add(video_parse)
        self.pipeline.add(video_decode)
        self.pipeline.add(sink)

        ##################################################################
        # Link pipeline elements

        logger.debug(f"{__file__} Linking elements in the Pipeline ...")
        source.link(video_depay)
        video_depay.link(video_parse)
        # video_parse.link(video_decode)
        video_parse.link(video_decode)
        video_decode.link(sink)

        self.pipeline.set_state(Gst.State.READY)

    def clean_up(self):
        try:
            logger.info(f"{__file__}[bus_call] Attempting to kill video-src")
            v_src = self.pipeline.get_by_name('source')
            if v_src:
                v_src.set_state(Gst.State.PAUSED)
        except Exception as videoSrcException:
            logger.warning(f'{__file__} [bus_call] Warning: videoSrc {videoSrcException}')

        self.pipeline.set_state(Gst.State.PAUSED)
        logger.info(f"{__file__} clean_up: finished clean up of sources")

    def run(self):
        # Loop forever so that if connection is lost we just reboot and try again!
        while self.run_flag:
            try:
                logger.info(f"{__file__} Starting pipeline ...")
                self.pipeline.set_state(Gst.State.PLAYING)
                self.runtime_clock['start'] = datetime.now()
                self.loop.run()

            except Exception as pipelineErr:
                logger.warning(f"{__file__} Unknown error occurred during run time: {pipelineErr}")

            finally:
                logger.info(f"{__file__} quit loop, starting clean up")
                self.clean_up()
                logger.info(f'{__file__} clean up complete ... printing out statistics ...')
                self.pipeline.set_state(Gst.State.NULL)

        # Calculate runtime stats
        self.runtime_clock['stop'] = datetime.now()
        total_seconds = self.runtime_clock['stop'].timestamp() - self.runtime_clock['start'].timestamp()
        self.runtime_clock['runtime'] = sec_to_hms(total_seconds)
        # scripts stats printed to terminal
        logger.info(f"{__file__} Pipeline runtime clock ...\n"
                     f"\t\tstart:      {self.runtime_clock['start']} \n"
                     f"\t\tstop:       {self.runtime_clock['stop']}  \n"
                     f"\t\truntime:    {self.runtime_clock['runtime']} \n"
                     )


if __name__ == '__main__':
    """
    Dev notes: This is how to clear gstreamer cache on device
        rm ${HOME}/.cache/gstreamer-1.0/registry.x86_64.bin
        rm ${HOME}/.cache/gstreamer-1.0/registry.aarch64.bin
    """
    from gstreamer.common_utils.setup_logging import setup_logging
    setup_logging()

    conf = {
        "url": "rtsp://192.168.1.69:8554/camera1"
    }
    application = RtspClient(conf=conf)
    try:
        application.run()
    except Exception as err:
        logger.error(f"[{str(__file__)}.main] ERROR: {err}")
        logger.error(f"[{str(__file__)}.main] Exiting program ...")
    finally:
        sys.exit(1)
