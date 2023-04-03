
import gi
import logging
gi.require_version('Gst', '1.0')
from gi.repository import Gst


def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        logging.info("End-of-stream\n")
        loop.quit()
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        logging.warning("Warning: %s: %s\n" % (err, debug))
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        logging.error("Error: %s: %s\n" % (err, debug))
        loop.quit()
    return True
