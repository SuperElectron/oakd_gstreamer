import logging
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst
from platform import uname
from datetime import datetime
import pytz
import netifaces as ni
import socket
import json

logger = logging.getLogger(__name__)


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj,'reprJSON'):
            return obj.reprJSON()
        else:
            return json.JSONEncoder.default(self, obj)


def is_aarch64():
    return uname()[4] == 'aarch64'

def link_src_pad_on_request(src, new_pad, link_element, mode):
    """
    dynamic pad callback for tsdemux (expects link_element={video, klv}, or one element)
    """
    element_names = None
    if isinstance(link_element, dict):
        try:
            klv_element = link_element['klv']
            video_element = link_element['video']
            element_names = [link_element['klv'], link_element['video']]
        except Exception as err:
            logging.error(f"[{mode}]: {err}")
            raise TypeError
    else:
        element_names = [link_element.get_name(), link_element.get_name()]
        video_element = link_element
        klv_element = link_element

    logging.info(f"[{mode}]: on_pad_added called! Received new pad '{new_pad.get_name()}' from '{src.get_name()}")
    new_pad_caps = new_pad.get_current_caps()
    new_pad_struct = new_pad_caps.get_structure(0)
    new_pad_type = new_pad_struct.get_name()

    if 'private' in new_pad.get_name():
        link_sink_pad = klv_element.get_static_pad("sink")
        element_name = element_names[0]

    elif 'video' in new_pad.get_name():
        # handle dataflow for video
        link_sink_pad = video_element.get_static_pad("sink")
        element_name = element_names[1]
    else:
        logging.warning(f"[{mode}]: Unexpected pad type for tsdemux: {new_pad.get_name}")
        raise ValueError

    if not link_sink_pad:
        logging.error(f"[{mode}]: Unable to get sink pad of the element you want to link")
        raise RuntimeError

    logging.info(
        f"[{mode}]: Link src pad ({new_pad.get_name()}:{new_pad_type}) "
        f"to sink pad ({element_name})")

    linking_status = new_pad.link(link_sink_pad)
    if linking_status != Gst.PadLinkReturn.OK:
        logging.error(f"[{mode}]: LINKING FAILURE {new_pad.get_name()}: "
                      f"Type is '{new_pad_type}' but link failed")
        raise RuntimeError

    logging.info(f"[{mode}]: LINKING SUCCESS: {src.get_name()}:{new_pad.get_name()} (type '{new_pad_type}')")
    return

def save_debug_log(pipeline, file_name=None, log_dir=None):
    logger.info(f"{file_name} Saving pipeline debug log ...")
    try:
        writable = Gst.debug_bin_to_dot_data(pipeline, Gst.DebugGraphDetails.ALL)
    except Exception as err:
        logger.error(f"{file_name} Error with Gst.debug_bin_to_dot_data: {err}")
        raise RuntimeError

    if log_dir:
        log_file = f"{log_dir}/{file_name}.pipeline"
    else:
        log_file = f"/gstreamer/logs/{file_name}.pipeline"

    try:
        with open(f'{log_file}.dot', 'w', encoding="UTF-8") as f:
            f.write(writable)
        # logger.debug(f"[{file_name}] "
        #              f"Finished saving gstreamer DEBUG_DUMP_DOT: {log_file}.dot")
        # logger.debug(f"\n\n{10 * '*'}\nTry this to view the block diagram: "
        #              f"\ncd {log_file}.dot;\ndot -Tpng {log_file}.dot > {log_file}.png\n{10 * '*'}\n")
    except Exception as err:
        logger.error(f"[{file_name}] Error writing to file: {err}")
        logger.error(f"[{file_name}] File path error with log_dir=({log_file})")


def save_debug_dot(pipeline, file_name=None, state=None, log_dir=None):
    _log_prefix = "[save_debug_dot]\n-- "
    assert file_name is not None
    assert log_dir is not None
    assert state is not None

    try:
        writable = Gst.debug_bin_to_dot_data(pipeline, Gst.DebugGraphDetails.ALL)
    except Exception as err:
        logger.error(f"{_log_prefix} Error with Gst.debug_bin_to_dot_data: {err}")
        raise RuntimeError

    log_file = f"{log_dir}/{file_name}.{state}"

    try:
        with open(f'{log_file}.dot', 'w', encoding="UTF-8") as f:
            f.write(writable)
        logger.debug(f"{_log_prefix} "
                     f"Finished saving gstreamer DEBUG_DUMP_DOT: {log_file}.dot")
    except Exception as err:
        logger.error(f"[{file_name}] Error writing to file: {err}")
        logger.error(f"[{file_name}] File path error with log_dir=({log_file})")


def sec_to_hms(seconds):
    if not isinstance(seconds, float):
        raise RuntimeError("Expects float as argument output.")

    hours = seconds // 3600
    # remaining seconds
    seconds -= (hours * 3600)
    # minutes
    minutes = seconds // 60
    # remaining seconds
    seconds -= (minutes * 60)
    milliseconds = str(int(100 * (seconds - int(seconds)))).zfill(2)
    ret_val = f"{str(int(hours)).zfill(2)}:{str(int(minutes)).zfill(2)}:" \
              f"{str(int(seconds)).zfill(2)}.{milliseconds[0:2]}"
    return ret_val


def get_host_name_ip_socket():
    try:
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)
        logger.info(f"Hostname : {host_name}")
        logger.info(f"IP : {host_ip}")
        return str(host_ip)
    except Exception as exp:
        logger.error(f"Unable to get Hostname and IP: {exp}")
        raise RuntimeError


def get_host_name_ip_iface():
    try:
        ni.ifaddresses('eth0')
        ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        logger.info(f"Detected Hostname Ip: {ip}")
        return str(ip)
    except Exception as exp:
        logger.error(f"Unable to get Hostname and IP: {exp}")
        raise RuntimeError


def create_timestamp(timezone="America/Vancouver"):
    """
    Creates iso timestamp of form: '2016-11-16T22:31:18.130822+00:00'
    """
    assert isinstance(timezone, str)
    utc_now = pytz.utc.localize(datetime.utcnow())
    utc_now = utc_now.astimezone(pytz.timezone(timezone))
    human_readable = utc_now.strftime("%Y-%b-%dT%H:%M:%S %Z")
    utc = round(utc_now.timestamp(), 2)
    return human_readable, float(utc)


def timestamp_converter(time_stamp: str) -> float:
    from datetime import datetime
    """
    Converts time stamp to epoch: ret = timestamp_converter('2020-05-23 18:12:40.461252+00:00')
    @input: '2020-05-23 18:12:40.461252+00:00'
    @return: 123456.1234
    """
    try:
        date, time = time_stamp.split(" ")
        year, month, day = date.split("-")
        time, tz = time.split("+")
        hour, minute, second = time.split(":")
        second = second.split(".")
        if len(second) == 1:
            seconds = second[0]
            microseconds = "00"
        else:
            seconds = second[0]
            microseconds = second[1]

    except Exception as err:
        logger.error(f"timestamp_converter() while extracting components for timestamp ({time_stamp}): {err}\n\n")
        raise RuntimeError

    try:
        ts_new = datetime(
            year=int(year), month=int(month), day=int(day),
            hour=int(hour), minute=int(minute), second=int(seconds), microsecond=int(microseconds),
        )
        ret = ts_new.timestamp()
        return ret
    except Exception as err:
        logger.error(f"timestamp_converter() for creating datetime from timestamp ({time_stamp}): {err}\n\n")
