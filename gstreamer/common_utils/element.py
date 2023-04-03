import logging
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from contextlib import contextmanager
import ctypes
import typing as typ
from fractions import Fraction
from collections import deque


class GstMapInfo(ctypes.Structure):
    _fields_ = [('memory', ctypes.c_void_p),  # GstMemory *memory
                ('flags', ctypes.c_int),  # GstMapFlags flags
                ('data', ctypes.POINTER(ctypes.c_byte)),  # guint8 *data
                ('size', ctypes.c_size_t),  # gsize size
                ('maxsize', ctypes.c_size_t),  # gsize maxsize
                ('user_data', ctypes.c_void_p * 4),  # gpointer user_data[4]
                ('_gst_reserved', ctypes.c_void_p * 4)]  # GST_PADDING


class BufferManager:

    def __init__(self,
                 total_time=0, object_memory=5, debug_count=50,
                 fps: typ.Union[Fraction, int] = Fraction("60000/1001")):
        self._debug_count = debug_count
        self.total_time = total_time

        # debugging for buffer_probe_timing()
        self.last_pts = deque(maxlen=5)
        self.last_dts = deque(maxlen=5)
        self.last_total_time = 0
        self.no_value = GLib.MAXUINT64
        self.frame_count = -1

        # debugging for identity element's 'handoff' callbacks
        self.identity_check_count = -1
        self.identity_parse_count = -1
        self.identity_fix_count = -1
        self.identity_track_count = {
            "original": deque(maxlen=100),
            "updated": deque(maxlen=100),
            "current": deque(maxlen=100)
        }
        self.fps = fps
        # Set up for setup_writable_buffer()
        self.libgst = ctypes.CDLL('libgstreamer-1.0.so.0')
        self.setup_writable_buffer()
        self.info_data = b''

    def setup_writable_buffer(self):
        self.libgst.gst_context_writable_structure.restype = ctypes.c_void_p
        self.libgst.gst_context_writable_structure.argtypes = [ctypes.c_void_p]
        self.libgst.gst_structure_set.restype = ctypes.c_void_p
        self.libgst.gst_structure_set.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]

        GST_MAP_INFO_POINTER = ctypes.POINTER(GstMapInfo)
        self.libgst.gst_buffer_map.argtypes = [ctypes.c_void_p, GST_MAP_INFO_POINTER, ctypes.c_int]
        self.libgst.gst_buffer_map.restype = ctypes.c_int
        self.libgst.gst_buffer_unmap.argtypes = [ctypes.c_void_p, GST_MAP_INFO_POINTER]
        self.libgst.gst_buffer_unmap.restype = None
        self.libgst.gst_mini_object_is_writable.argtypes = [ctypes.c_void_p]
        self.libgst.gst_mini_object_is_writable.restype = ctypes.c_int

    @contextmanager
    def map_gst_buffer(self, pbuffer, flags):
        if pbuffer is None:
            raise TypeError("Cannot pass NULL to map_gst_buffer")

        ptr = hash(pbuffer)
        if flags & Gst.MapFlags.WRITE and self.libgst.gst_mini_object_is_writable(ptr) == 0:
            raise ValueError("Writable array requested but buffer is not writeable")

        mapping = GstMapInfo()
        success = self.libgst.gst_buffer_map(ptr, mapping, flags)

        if not success:
            raise RuntimeError("Couldn't map buffer")

        try:
            # Cast POINTER(c_byte) to POINTER to array of c_byte with size mapping.size
            # Returns not pointer but the object to which pointer points
            yield ctypes.cast(mapping.data, ctypes.POINTER(ctypes.c_byte * mapping.size)).contents
        finally:
            self.libgst.gst_buffer_unmap(ptr, mapping)

    def buffer_probe_timing(self,
                            pad, info, user_data,
                            fps: typ.Union[Fraction, int] = Fraction("60000/1001")) -> Gst.PadProbeReturn:
        """
        identity-elem
        """
        gst_buffer = info.get_buffer()
        message_format = f"[{user_data}]: buffer_probe_timing()| "
        if not gst_buffer:
            logging.error(f"{message_format} message: Unable to get GstBuffer")
            return Gst.PadProbeReturn.PASS

        if isinstance(gst_buffer, Gst.Buffer):
            (result, buffer_info) = gst_buffer.map(Gst.MapFlags.READ)

            if isinstance(buffer_info, Gst.MapInfo):
                try:
                    # Frame count starts at -1, so the first frame will have zero total_time
                    self.frame_count += 1
                    # Gst.util_uint64_scale_int(1, Gst.SECOND, (fps.numerator/fps.denominator)) will drift over time!
                    fps_time_step = Gst.SECOND / (fps.numerator / fps.denominator)
                    self.total_time = int(fps_time_step * self.frame_count)

                    my_pts = self.total_time
                    my_dts = self.total_time

                    # if self.no_value in [gst_buffer.pts, gst_buffer.dts]:
                    #     print(f"{message_format} Found incorrect pts or dts")
                    # if self.no_value in [gst_buffer.duration]:
                    #     print(f"{message_format} Found incorrect duration")

                    if self.frame_count % self._debug_count == 0:
                        print(f"{message_format} frame ({self.frame_count}), "
                              f"fps= {fps.numerator}/{fps.denominator}, "
                              f"fps_time_step= {fps_time_step} ,"
                              f"total_time= {self.total_time} ,"
                              f"\n")

                    # gather buffer items
                    self.last_dts.append(gst_buffer.dts)
                    self.last_pts.append(gst_buffer.pts)

                    buffer_info = Gst.Buffer.new_wrapped(buffer_info.data)
                    buffer_info.pool = gst_buffer.pool
                    buffer_info.pts = my_pts
                    buffer_info.dts = my_dts
                    buffer_info.duration = fps_time_step
                    buffer_info.offset_end = gst_buffer.offset_end
                    buffer_info.offset = gst_buffer.offset

                    buffer_info.mini_object.type = gst_buffer.mini_object.type
                    buffer_info.mini_object.refcount = gst_buffer.mini_object.refcount
                    buffer_info.mini_object.lockstate = gst_buffer.mini_object.lockstate

                except Exception as buffer_error:
                    raise RuntimeError(f"{message_format} message: "
                                       f"Caught error while trying to get buffer contents: {buffer_error}")
        return Gst.PadProbeReturn.OK

    def unpack_buffer(self, buffer: Gst.Buffer, display=False, name=None, counter: int = -1) -> dict:
        if not buffer.pool:
            pool = "None"
        else:
            pool = buffer.pool if buffer.pool else "None"

        buffer_dict = {
            "refcount": buffer.mini_object.refcount,
            "lockstate": buffer.mini_object.lockstate,
            "flags": buffer.mini_object.flags,
            "offset_end": buffer.offset_end,
            "pts": buffer.pts,
            "dts": buffer.dts,
            "duration": buffer.duration,
            "offset": buffer.offset,
            "pool": pool,
            "frame_count": counter,
        }
        if display:
            print(f"\n{'*' * 100}")
            print(f"[identity-callback ({name})] buffer {counter:<5}")
            print(
                f" refcount: {buffer_dict['refcount']:>30} | lockstate: {buffer_dict['lockstate']:>30} |      flags: {buffer_dict['flags']:>30}")  # noqa 501
            print(
                f" duration: {buffer_dict['duration']:>30} |    offset: {buffer_dict['offset']:>30} | offset_end: {buffer_dict['offset_end']:>30}")  # noqa 501
            print(
                f"     pool: {buffer_dict['pool']:>30} |       pts: {buffer_dict['pts']:>30} |        dts: {buffer_dict['dts']:>30}")  # noqa 501
        return buffer_dict

    def generate_new_buffer(self, element_buffer: Gst.Buffer, fps_time_step, total_time, display=False) -> Gst.Buffer:

        if isinstance(element_buffer, Gst.Buffer):
            (result, buffer_info) = element_buffer.map(Gst.MapFlags.READ | Gst.MapFlags.WRITE)

            if isinstance(buffer_info, Gst.MapInfo):
                buffer_copy = self.unpack_buffer(element_buffer)
                if buffer_copy['pool'] and buffer_copy['pool'] != 'None':
                    buffer_info.pool = buffer_copy['pool']

                new_buffer = Gst.Buffer.new_wrapped(buffer_info.data)
                new_buffer.pts = total_time
                new_buffer.dts = total_time
                new_buffer.duration = fps_time_step
                new_buffer.offset_end = buffer_copy['offset_end']
                new_buffer.offset = buffer_copy['offset']

                # previous = self.identity_track_count['previous'].popleft()
                # # debugging
                # if display:
                #     print("****************************")
                #     # print(f"element_buffer (type: ({type(element_buffer)}), values({element_buffer.data}))")
                #     print(f"element_buffer (type: {type(element_buffer)})")
                #     print(f"new_buffer = Gst.Buffer.new_wrapped(buffer_info.data)::  "
                #           f"new_buffer(type): {type(new_buffer)}")
                #     print()
                #
                # if previous['pts'] != buffer_copy['pts']:
                #     msg = f"previous['pts'] != buffer_copy['pts']. " \
                #           f"previous({previous['pts']}), current({buffer_copy['pts']})"
                #     print(msg)
                #     raise RuntimeError(msg)

        return new_buffer
