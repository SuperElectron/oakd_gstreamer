#!/usr/bin/env python3

# https://lazka.github.io/pgi-docs/GstRtspServer-1.0/classes/RTSPServer.html

import cv2
import gi
import logging
from threading import Thread
import calendar
from datetime import datetime

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GstRtspServer, GLib, GstApp, GObject

logger = logging.getLogger(__name__)
logging.getLogger(__name__).setLevel(logging.WARNING)


class SensorFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, pipeline_conf, **properties):
        super(SensorFactory, self).__init__(**properties)
        self.name = pipeline_conf["name"]

        if pipeline_conf["source"]["type"] == "file":
            self.cap = cv2.VideoCapture(pipeline_conf["source"]["location"])
        elif pipeline_conf["source"]["type"] == "webcam":
            self.cap = cv2.VideoCapture(0)
        elif pipeline_conf["source"]["type"] == "oakd":
            self.cap = None
            logging.info(f"[{self.name}] Connecting to oakd camera capture")
        elif pipeline_conf["source"]["type"] == "file_av":
            self.cap = None
        else:
            logging.warning(f"[{self.name}] Invalid configuration for SensoryFactory")
            raise RuntimeError

        self.run_flag = True
        self.number_frames = 0
        self.fps = pipeline_conf["fps"]
        self.width = pipeline_conf["width"]
        self.height = pipeline_conf["height"]
        self.duration = 1 / self.fps * Gst.SECOND  # duration of a frame in nanoseconds
        logger.info(
            f"[{pipeline_conf['name']}] Setting configs: fps={self.fps}, width={self.width}, height={self.height}")

        # create objects for RTSP pipeline
        self.pipeline = self.create_rtsp_pipeline(pipeline_conf["source"])
        self.source = self.pipeline.get_by_name("source")

        # create objects for recording pipeline
        self.record_pipeline = self.create_filesink_pipeline()
        self.record_source = self.record_pipeline.get_by_name("source_record")
        self.record_loop = None
        self.record_bus = None
        self.record_thread = Thread(target=self.record, daemon=True)

    def record(self):
        try:
            logger.info()
            self.record_pipeline.set_state(Gst.State.PLAYING)
            self.record_loop.run()
        except Exception as RecordingException:
            logger.error(f"{__file__} [record] error: {RecordingException}")
        finally:
            self.record_pipeline.set_state(Gst.State.NULL)

    def stop_record(self):
        self.record_pipeline.send_event(Gst.event_new_eos())

    def setup_recording_pipeline(self):
        self.record_pipeline = self.create_filesink_pipeline()
        self.record_source = self.record_pipeline.get_by_name("source_record")
        self.record_loop = GObject.MainLoop()
        self.record_bus = self.record_pipeline.get_bus()
        self.record_bus.add_signal_watch()
        self.record_bus.connect("message", self.bus_call, self.record_loop)

    def bus_call(bus, message, loop):
        t = message.type
        if t == Gst.MessageType.EOS:
            logger.info("End-of-stream\n")
            loop.quit()
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            logger.warning("Warning: %s: %s\n" % (err, debug))
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error("Error: %s: %s\n" % (err, debug))
            loop.quit()
        return True

    def create_src_caps(self):
        src_caps = f"do-timestamp=true is-live=true block=true format=GST_FORMAT_TIME" \
                   f"caps=" \
                   f"video/x-raw," \
                   f"format=BGR," \
                   f"width=(int){self.width}," \
                   f"height=(int){self.height}," \
                   f"framerate=(fraction){self.fps}/1"
        return src_caps

    @staticmethod
    def create_unix_timestamp():
        date = datetime.utcnow()
        utc_time = calendar.timegm(date.utctimetuple())
        return utc_time

    def create_rtsp_pipeline_string(self):
        src = f"appsrc name=source {self.create_src_caps()} "
        launch_string = f"{src} " \
                        "! videoconvert name=rtsp_vid_convert ! video/x-raw,format=I420 " \
                        "! x264enc name=rtsp_x264 speed-preset=fast tune=zerolatency " \
                        "! rtph264pay config-interval=1 name=pay0 pt=96"
        return launch_string

    def create_file_sink_string(self):
        now = self.create_unix_timestamp()
        file = f"/tmp/{now}-{self.name}_recording.ts"

        src = f"appsrc name=source_record {self.create_src_caps()} "
        launch_string = f"{src} " \
                        "! videoconvert name=record_convert ! video/x-raw,format=I420 " \
                        "! x264enc name=record_x264 speed-preset=fast tune=zerolatency " \
                        "! queue name=record_videoQ leaky=1" \
                        "! mpegtsmux name=record_mux " \
                        f"! filesink location={file} " \
                        "! pulsesrc " \
                        "! audioconvert " \
                        "! avenc_aac " \
                        "! queue leaky=1 name=name=record_audioQ " \
                        " record_mux."

        return launch_string

    @staticmethod
    def two_way_call(video_path):
        logger.info(f"{__file__} reading from file {video_path} ")
        src = f"filesrc location={video_path}"
        demux = "qtdemux name=demux mpegtsmux name=mux alignment=7"
        video_branch = "queue leaky=1 ! h264parse ! avdec_h264 ! x264enc"
        audio_branch = "queue leaky=1 ! mpegaudioparse !  mpg123audiodec !  audioconvert !  avenc_aac"

        launch_string = f" {src} ! {demux} ! tee name=v_t v_t. ! rtpmp2tpay name=pay0 " \
                        f"demux. ! {video_branch}  " \
                        f"! mux. demux. ! {audio_branch} " \
                        f"! mux."

        logger.info(f"{__file__} launch_string=\n{launch_string}\n")
        return launch_string

    def create_rtsp_pipeline(self, src):
        logger.info(f"{__file__} creating rtsp stream for {src}")
        if src['type'] == "file_av":
            launch_string = self.two_way_call(src['location'])
        else:
            launch_string = self.create_rtsp_pipeline_string()
        return Gst.parse_launch(launch_string)

    def create_filesink_pipeline(self):
        logger.info(f"{__file__} creating filesink pipeline for {self.name} ")
        launch_string = self.create_file_sink_string()
        return Gst.parse_launch(launch_string)

    def push(self, frame=None, src_name=None):
        _log_prefix = f"[push({src_name})]\n-- "
        assert frame is not None
        assert src_name is not None

        if self.number_frames % 100 == 0 or self.number_frames == 0:
            logger.debug(f"{_log_prefix} src=({src_name}) count=({self.number_frames})")

        if not self.run_flag:
            msg = f"{_log_prefix} self.run_flag is false, therefore the pipeline is down"
            logger.warning(msg)
            GstApp.AppSrc.end_of_stream(self.source)
            self.pipeline.send_event(Gst.event_new_eos())
            return
        try:
            data = frame.tobytes()
            buf = Gst.Buffer.new_allocate(None, len(data), None)
            buf.fill(0, data)
            buf.duration = self.duration
            timestamp = self.number_frames * self.duration
            buf.pts = buf.dts = int(timestamp)
            buf.offset = timestamp
            self.number_frames += 1
            rtsp_retval = self.source.emit('push-buffer', buf)
            if rtsp_retval != Gst.FlowReturn.OK:
                logger.error(f"Could not push buffer to rtsp pipeline: error_code={rtsp_retval}")
            logger.info(f"pushed buffer, "
                         f"frame {self.number_frames}, "
                         f"duration {self.duration} ns, "
                         f"durations {self.duration / Gst.SECOND} s ")

        except Exception as VideoSrcError:
            logger.error(f"{_log_prefix} VideoSrcError {VideoSrcError}")
            raise VideoSrcError

    def on_need_data(self, src, dummy):
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                data = frame.tobytes()
                buf = Gst.Buffer.new_allocate(None, len(data), None)
                buf.fill(0, data)
                buf.duration = self.duration
                timestamp = self.number_frames * self.duration
                buf.pts = buf.dts = int(timestamp)
                buf.offset = timestamp
                self.number_frames += 1
                rtsp_retval = self.source.emit('push-buffer', buf)
                if rtsp_retval != Gst.FlowReturn.OK:
                    logger.error(f"Could not push buffer to rtsp pipeline: error_code={rtsp_retval}")
                logger.info(f"pushed buffer, "
                             f"frame {self.number_frames}, "
                             f"duration {self.duration} ns, "
                             f"durations {self.duration / Gst.SECOND} s ")

    def do_create_element(self, url):
        return self.pipeline

    def do_configure(self, rtsp_media):
        self.number_frames = 0
        if self.cap is not None:
            self.source.connect('need-data', self.on_need_data)

    def link_to_filesink(self, gst_object, pad, u_data):
        now = self.create_unix_timestamp()
        file = f"/tmp/{now}-{self.name}_2wayCall.ts"

        sink = Gst.ElementFactory.make("filesink")
        sink.set_property("location", file)

        self.pipeline.add(sink)

        tee = self.pipeline.get_by_name("v_t")
        if not tee:
            logger.error(f"{__file__} Could not get tee from pipeline")
            raise RuntimeError

        tee.link(sink)


class GstServer(GstRtspServer.RTSPServer):
    def __init__(self, server_conf, **properties):
        super(GstServer, self).__init__(**properties)
        Gst.init(None)
        # Set basic server configs
        self.mount_points = self.get_mount_points()
        self.set_service(server_conf["port"])
        self.set_address(server_conf["ip_address"])

        self.file_sinks = []
        self.threads = []

        # configure camera streams
        self.pipelines = []
        pipeline_conf = server_conf["pipeline_conf"]
        for conf in pipeline_conf:
            appsrc = SensorFactory(conf)
            appsrc.set_shared(True)
            self.mount_points.add_factory(conf["extension"], appsrc)
            logger.info(f"Stream available: {server_conf['ip_address']}:{server_conf['port']}{conf['extension']}")
            self.pipelines.append(appsrc)

        # attach and continue
        self.attach(None)
        self.loop = GLib.MainLoop()
        self.thread = Thread(target=self.loop.run, daemon=True)


if __name__ == "__main__":

    # type=webcam, size=640,480
    # type=file, size=1920,1080
    # from gstreamer.src.server.app_config import rtsp_config as config
    config = {
        "ip_address": "192.168.1.69",
        "port": "8554",
        "pipeline_conf": [
            {
                "name": "camera1",
                "fps": 30,
                "width": 1920,
                "height": 1080,
                "source": {
                    "type": "file",
                    "location": "/gstreamer/sample_1080p_h264.mp4"
                },
                "extension": "/camera1"
            }
            # ,{
            #     "name": "camera2",
            #     "fps": 30,
            #     "width": 1920,
            #     "height": 1080,
            #     "source": {
            #         "type": "file",
            #         "location": "/gstreamer/sample_1080p_h264.mp4"
            #     },
            #     "extension": "/camera2"
            # },
            # {
            #     "name": "camera3",
            #     "fps": 30,
            #     "width": 1920,
            #     "height": 1080,
            #     "source": {
            #         "type": "webcam",
            #         "location": "/gstreamer/sample_1080p_h264.mp4"
            #     },
            #     "extension": "/camera3"
            # }
        ]
    }
    from gstreamer.common_utils.setup_logging import setup_logging

    setup_logging()

    server = GstServer(config)

    try:
        server.thread.start()
    except Exception as runTimeError:
        logger.error(f" Runtime Error: {runTimeError}")
    finally:
        server.thread.join()
    logger.info(f" FINISHED")

"""

------------------------------------------------------------------------------------------------

gst-launch-1.0 -e filesrc location=/gstreamer/bla.mp4 ! qtdemux name=demux \
    demux. ! queue ! h264parse ! avdec_h264 ! fakesink dump=true \
    demux. ! queue ! "audio/mpeg" ! mpegaudioparse ! mpg123audiodec ! audioconvert ! autoaudiosink
    
gst-launch-1.0 -e filesrc location=/gstreamer/bla.mp4 ! qtdemux name=demux \
    demux. ! queue ! h264parse !  fakesink dump=true \
    demux. ! queue ! "audio/mpeg" ! mpegaudioparse ! mpg123audiodec ! audioconvert ! autoaudiosink
    
gst-launch-1.0 -e filesrc location=/gstreamer/bla.mp4 ! qtdemux name=demux \
    demux. ! queue ! h264parse !  fakesink dump=true \
    demux. ! queue ! "audio/mpeg" ! mpegaudioparse ! autoaudiosink

gst-launch-1.0 -e filesrc location=/gstreamer/bla.mp4 ! qtdemux name=demux \
    demux. ! queue ! h264parse !  fakesink dump=true \
    demux. ! queue ! "audio/mpeg" ! mpegaudioparse ! fakesink dump=false

gst-launch-1.0 -e filesrc location=/gstreamer/bla.mp4 ! qtdemux name=demux \
    demux. ! queue ! h264parse ! avdec_h264 ! x264enc ! rtph264pay name=pay0 ! fakesink dump=true \
    demux. ! queue ! "audio/mpeg" ! mpegaudioparse ! mpg123audiodec !  audioconvert !  avenc_aac ! rtpmp4apay name=pay1 ! fakesink dump=false

------------------------------------------------------------------------------------------------

gst-launch-1.0 -e filesrc location=/gstreamer/bla.mp4 ! qtdemux name=demux \
    demux. ! queue leaky=1 ! video/x-h264 ! h264parse ! avdec_h264 ! x264enc ! rtph264pay name=pay0 ! fakesink dump=true \
    demux. ! queue leaky=1 ! "audio/mpeg" ! mpegaudioparse ! mpg123audiodec !  audioconvert !  avenc_aac ! rtpmp4apay name=pay1 ! fakesink dump=false

gst-launch-1.0 filesrc location=/gstreamer/bla.mp4 qtdemux name=demux  \
    demux. ! queue ! h264parse ! avdec_h264 ! x264enc ! rtph264pay name=pay0   \
    demux. ! queue ! audio/mpeg ! rtpmp4apay name=pay1

------------------------------------------------------------------------------------------------

filesrc location=/gstreamer/bla.mp4 \
  ! qtdemux name=demux mpegtsmux name=mux alignment=7 \
  ! rtpmp2tpay name=pay0 demux. \
  ! queue leaky=1 ! h264parse ! avdec_h264 ! x264enc ! mux. demux. \
  ! queue leaky=1 ! mpegaudioparse !  mpg123audiodec !  audioconvert !  avenc_aac ! mux."

gst-launch-1.0 -v rtspsrc location=rtsp://192.168.1.69:8554/camera1  \
  ! rtpmp2tdepay ! tsparse ! tsdemux name=demux demux. ! queue ! decodebin ! \
  videoconvert ! fpsdisplaysink text-overlay=false sync=false demux. ! queue leaky=1 ! decodebin ! audioconvert ! autoaudiosink sync=false

------------------------------------------------------------------------------------------------

gst-launch-1.0 -v pulsesrc ! audioconvert ! vorbisenc ! oggmux ! filesink location=alsasrc.ogg

gst-launch-1.0 -v pulsesrc ! audioconvert ! avenc_aac ! mpegtsmux ! filesink location=sound.ts

https://gist.github.com/liviaerxin/bb34725037fd04afa76ef9252c2ee875

"""
