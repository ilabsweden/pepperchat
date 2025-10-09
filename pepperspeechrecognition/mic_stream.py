import socket
import struct
import threading
import time
import traceback

def get_local_ip():
    # Gets the local IP of the default interface used for outbound connections
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def get_bar(normval, width):
    val = int(round(normval * width))
    return ("+"*val) + "-"*(width-val)

class MicStreamPacket:
    idx = 0
    pcm = bytes()

    def serialize(self):
        return struct.pack(_PACKET_HEADER_FMT, self.idx & 0xFFFFFFFF) + self.pcm

    @staticmethod
    def deserialize(data):
        # type: (bytes) -> MicStreamPacket
        ret = MicStreamPacket()
        ret.idx = struct.unpack(_PACKET_HEADER_FMT, data[:_PACKET_HEADER_SIZE])[0]
        ret.pcm = data[_PACKET_HEADER_SIZE:]
        return ret

_PACKET_HEADER_FMT = "!I"
_PACKET_HEADER_SIZE = 4

class MicStreamConfig:
    #receiver_ip = "192.168.0.104"
    receiver_ip = "224.1.1.5" # Multicast gor att vi inte behover fippla med olika ips i olika LAN
    udp_port = 50005
    sample_rate = 16000
    channel_cnt = 1
    sample_fmt = "int16"
    packet_dur_ms = 20

    def is_multicast(self):
        parts = self.receiver_ip.split(".")
        return len(parts) == 4 and (224 <= int(parts[0]) <= 239)
    
    def get_bytes_per_sample(self):
        if self.sample_fmt == "int16":
            return 2
        return 2

    def get_frames_per_packet(self):
        return self.sample_rate * self.packet_dur_ms//1000

    def get_bytes_per_frame(self):
        return self.get_bytes_per_sample() * self.channel_cnt

    def get_bytes_per_packet(self):
        return _PACKET_HEADER_SIZE + self.get_frames_per_packet() * self.get_bytes_per_frame()

    def get_norm_peak(self, pcm, channel = 0):
        if self.sample_fmt == "int16":
            peak = 0
            bps = self.get_bytes_per_sample()
            bpf = self.get_bytes_per_frame()
            for i in range(int(len(pcm)/bpf)):
                offs = i*bpf
                peak=max(peak,struct.unpack("h", pcm[offs:offs+bps])[0])
            return peak / float(0x7FFF)
        return 0

    def get_peak_bar(self, pcm, channel = 0, width = 20, gamma = .3):
        return get_bar(self.get_norm_peak(pcm, channel) ** gamma, width)
    

class MicStreamSender:
    def __init__(self, cfg):
        # type: (MicStreamConfig) -> str
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        if cfg.is_multicast():
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)  # TTL = 1 local network
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(get_local_ip()))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 64 * 1024)
        self.cfg = cfg
        self.packet = MicStreamPacket()

    def send_pcm(self, pcm):
        # type: (bytes) -> None
        self.packet.pcm = pcm
        self.packet.idx += 1
        self.sock.sendto(self.packet.serialize(), (self.cfg.receiver_ip, self.cfg.udp_port))

    def close(self):
        self.sock.close()



class MicStreamReceiver:
    STATE_IDLE = "Idle"
    STATE_WAITING = "Waiting for data"
    STATE_RECEIVING = "Receiving data"
    def __init__(self, cfg, pcm_callback, state_change_callback = None):
        # type: (MicStreamConfig, function[None,[bytes]], function[None,[str]]) -> None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 64 * 1024)
        self.packet_size = cfg.get_bytes_per_packet()
        self.cfg = cfg
        self.listening = False
        self.getting_data = False
        self.pcm_callback = pcm_callback
        self.state_change_callback = state_change_callback
        self.state = self.STATE_IDLE
    
    def _set_state(self, state):
        if state == self.state:
            return
        print(self.__class__.__name__, state)
        self.state = state
        if self.state_change_callback:
            self.state_change_callback(state)

    def listen(self):
        self.sock.bind(("", self.cfg.udp_port))
        if self.cfg.is_multicast():
            self._multicast_req = struct.pack("4s4s", socket.inet_aton(self.cfg.receiver_ip), socket.inet_aton(get_local_ip()))
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, self._multicast_req)        
        self.last_receive_time = 0
        
        def watch_feed():
            age_threshold = self.cfg.packet_dur_ms / 500.0
            while self.listening:
                ok = time.time() - self.last_receive_time < age_threshold
                if ok != (self.state == self.STATE_RECEIVING):
                    self._set_state(self.STATE_RECEIVING if ok else self.STATE_WAITING)
                time.sleep(age_threshold)

        def doit():
            self.listening = True
            prev_idx = 0
            self._set_state(self.STATE_WAITING)
            while self.listening:
                try:
                    data, _ = self.sock.recvfrom(self.packet_size + 64)
                    if len(data) >= self.packet_size:
                        packet = MicStreamPacket.deserialize(data)
                        if self.state == self.STATE_RECEIVING:
                            idx_diff = packet.idx - prev_idx
                            if idx_diff != 1:
                                print(self.__class__.__name__,"idx diff:",idx_diff)
                        prev_idx = packet.idx
                        self.last_receive_time = time.time()
                        if self.listening:
                            self.pcm_callback(packet.pcm)
                except:
                    if self.listening:
                        traceback.print_exc()

        threading.Thread(target=doit, daemon=True).start()
        threading.Thread(target=watch_feed, daemon=True).start()
    
    def close(self):
        self.listening = False
        if self.cfg.is_multicast():
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, self._multicast_req)
        self.sock.close()
        self._set_state(self.STATE_IDLE)