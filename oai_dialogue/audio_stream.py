# -*- coding: utf-8 -*-
# Should be kept useable by python2
import struct
import threading
import time
import traceback

import numpy as np

try:
    from udp import UdpSender, UdpReceiver
except ImportError:
    from oai_dialogue.udp import UdpSender, UdpReceiver

DEFAULT_MULTICAST_IP = "224.1.1.5"
DEFAULT_UDP_PORT = 50005

_PACKET_HEADER_FMT = "!IIII"
_PACKET_HEADER_SIZE = 16

class AudioStreamPacket:
    # We dont want to deal with padding, so header vals are all 32 bit
    idx = 0
    sample_rate = 16000
    channel_cnt = 1
    pcm_size = 0
    pcm16_bytes = bytes()

    def serialize(self):
        return struct.pack(_PACKET_HEADER_FMT, 
            self.idx & 0xFFFFFFFF,
            self.sample_rate & 0xFFFFFFFF,
            self.channel_cnt & 0xFFFFFFFF,
            self.pcm_size & 0xFFFFFFFF,
        ) + self.pcm16_bytes

    @staticmethod
    def deserialize(data):
        # type: (bytes) -> AudioStreamPacket
        if len(data) > _PACKET_HEADER_SIZE:
            ret = AudioStreamPacket()
            ret.idx, ret.sample_rate, ret.channel_cnt, ret.pcm_size = struct.unpack(_PACKET_HEADER_FMT, data[:_PACKET_HEADER_SIZE])
            # Kanske kolla pcm_size?
            ret.pcm16_bytes = data[_PACKET_HEADER_SIZE:]
            return ret

def get_norm_peak(channel_cnt, pcm, channel = 0):
    peak = 0
    bytes_per_sample = 2
    bytes_per_frame = 2 * channel_cnt
    for i in range(int(len(pcm)/bytes_per_frame)):
        offs = i*bytes_per_frame
        peak=max(peak,struct.unpack("h", pcm[offs:offs+bytes_per_sample])[0])
    return peak / float(0x7FFF)

def get_peak_bar(channel_cnt, pcm, channel = 0, width = 20, gamma = .3):
    peak = get_norm_peak(channel_cnt, pcm, channel) ** gamma
    cnt = int(round(peak * width))
    return ("+"*cnt) + "-"*(width-cnt)
    

class AudioStreamSender(object):
    def __init__(self, sample_rate, channel_cnt, udp_port, receiver_ip):
        # type: (int, int, int, str) -> AudioStreamSender
        self.udp_sender = UdpSender(udp_port, receiver_ip)
        self.packet = AudioStreamPacket()
        self.packet.sample_rate = sample_rate
        self.packet.channel_cnt = channel_cnt
    
    @property
    def sample_rate(self):
        return self.packet.sample_rate
    @sample_rate.setter
    def sample_rate(self, val):
        self.packet.sample_rate = val

    @property
    def channel_cnt(self):
        return self.packet.channel_cnt
    @channel_cnt.setter
    def channel_cnt(self, val):
        self.packet.channel_cnt = val

    def send_pcm16_bytes(self, pcm):
        # type: (bytes) -> None
        self.packet.pcm16_bytes = pcm
        self.packet.idx += 1
        self.udp_sender.send_data(self.packet.serialize())

    def send_pcm16_frames(self, frames):
        # type: (np.ndarray) -> None
        self.send_pcm16_bytes(frames.tobytes())

    def close(self):
        self.udp_sender.close()

class AudioStreamReceiver:
    STATE_NOT_RUNNING = "Not running"
    STATE_WAITING = "Waiting for data"
    STATE_RECEIVING = "Receiving data"
    def __init__(self, udp_port, multicast_ip = None):
        # type: (int, str) -> AudioStreamReceiver
        self._running = threading.Event()
        self._lock = threading.Lock()
        self.getting_data = False
        self.pcm_callbacks = [] # list of callables (int, int, bytes) -> None
        self.state_change_callbacks = [] # list of callables (str) -> None
        self.state = self.STATE_NOT_RUNNING
        self._udp_parms = (udp_port, multicast_ip) 

    def add_pcm_callback(self, callback):
        """
        Registers a function (sample_rate:int, channel_cnt:int, pcm:bytes)
        that will be called when audio data is available.
        """
        if callback not in self.pcm_callbacks:
            self.pcm_callbacks.append(callback)

    def remove_pcm_callback(self, callback):
        "Removes a previously added callback."
        if callback in self.pcm_callbacks:
            self.pcm_callbacks.remove(callback)

    def add_state_change_callback(self, callback):
        "Registers a function that takes str as argument. This will receive state changes when they occur."
        if callback not in self.state_change_callbacks:
            self.state_change_callbacks.append(callback)

    def remove_state_change_callback(self, callback):
        "Removes a previously added callback."
        if callback in self.state_change_callbacks:
            self.state_change_callbacks.remove(callback)

    def _set_state(self, state):
        with self._lock:
            if state == self.state:
                return
            print(self.__class__.__name__, state)
            self.state = state
        for callback in self.state_change_callbacks:
            try:
                callback(state)
            except:
                traceback.print_exc()
    
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()
        return False

    def start(self):
        if self._running.is_set():
            print(self.__class__.__name__, "already started")
            return self
        self._running.set()
        self._set_state(self.STATE_WAITING)
        self.last_receive_time = 0
        self.prev_packet = None # type: AudioStreamPacket
        incomplete_frame_bytes = bytearray()
        BYTES_PER_SAMPLE = 2
        def on_receive(data):
            try:
                packet = AudioStreamPacket.deserialize(data)
                if packet and self._running.is_set():
                    with self._lock:
                        state = self.state
                        self.last_receive_time = time.time()

                    if self.prev_packet and (self.prev_packet.channel_cnt != packet.channel_cnt or self.prev_packet.sample_rate != packet.sample_rate):
                        incomplete_frame_bytes.clear()
                    
                    bytecnt_per_frame = BYTES_PER_SAMPLE * packet.channel_cnt
                    pcm_bytes = packet.pcm16_bytes
                    if incomplete_frame_bytes:
                        pcm_bytes = bytes(incomplete_frame_bytes) + pcm_bytes
                        incomplete_frame_bytes.clear()

                    remaining_byte_cnt = len(pcm_bytes) % bytecnt_per_frame
                    if remaining_byte_cnt:
                        incomplete_frame_bytes.extend(pcm_bytes[-remaining_byte_cnt:])
                        pcm_bytes = pcm_bytes[:-remaining_byte_cnt]
                    
                    incoming_frame_cnt = len(pcm_bytes) // bytecnt_per_frame
                    if incoming_frame_cnt > 0:
                        frames = np.frombuffer(pcm_bytes, dtype="<i2").reshape(-1, packet.channel_cnt)
                        for callback in self.pcm_callbacks:
                            try:
                                callback(packet.sample_rate, packet.channel_cnt, frames)
                            except:
                                traceback.print_exc()
                    
                    if self.prev_packet and state == self.STATE_RECEIVING:
                        idx_diff = packet.idx - self.prev_packet.idx
                        if idx_diff != 1:
                            print(self.__class__.__name__,"idx diff:",idx_diff)
                    self.prev_packet = packet
            except:
                if self._running.is_set():
                    traceback.print_exc()

       
        def loop():
            with UdpReceiver(on_receive, *self._udp_parms):
                age_threshold = .1 # TODO: Uppskatta förväntad tid från flödet
                while self._running.is_set():
                    with self._lock:
                        t = self.last_receive_time
                        state = self.state
                    
                    ok = time.time() - t < age_threshold
                    if ok != (state == self.STATE_RECEIVING):
                        self._set_state(self.STATE_RECEIVING if ok else self.STATE_WAITING)
                    time.sleep(age_threshold)

        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()
        return self
    
    def stop(self):
        self._running.clear()
        self.thread.join(timeout=2.0)
        # if self.udp_receiver:
        #     self.udp_receiver.stop()
        #     self.udp_receiver = None
        self._set_state(self.STATE_NOT_RUNNING)

