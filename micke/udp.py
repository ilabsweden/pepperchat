import socket
import struct
import sys
import threading
import time
import traceback
IS_PY2 = sys.version_info[0] == 2

def get_local_ip():
    # Gets the local IP of the default interface used for outbound connections
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def is_multicast_ip(ip):
    if ip:
        parts = ip.split(".")
        return len(parts) == 4 and (224 <= int(parts[0]) <= 239)

class UdpSender:
    def __init__(self, port, receiver_ip, max_buf_size = 65536):
        self.address = (receiver_ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        if is_multicast_ip(receiver_ip):
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)  # TTL = 1 local network
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(get_local_ip()))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, max_buf_size)
    def send_data(self, data):
        self.sock.sendto(data, self.address)
    def close(self):
        self.sock.close()

class UdpReceiver:
    def __init__(self, callback, port, multicast_ip=None, max_buf_size = 65536):
        self.callback = callback
        self.port = port
        self.max_buf_size = max_buf_size
        self.multicast_req = None
        if is_multicast_ip(multicast_ip):
            self.multicast_req = struct.pack("4s4s", socket.inet_aton(multicast_ip), socket.inet_aton(get_local_ip()))
        self._sock = None # type:socket.socket
        self._stop = threading.Event()
        self._thread = None # type:threading.Thread
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        
        def receive_loop():
            if s is None:
                return
            while not self._stop.is_set():
                try:
                    data, _ = s.recvfrom(self.max_buf_size)
                except socket.timeout:
                    continue
                except OSError:
                    # Likely closed during shutdown
                    break
                except Exception:
                    traceback.print_exc()
                    continue

                try:
                    self.callback(data)
                except Exception:
                    traceback.print_exc()       
        self._sock = s
        try:
            # Help reuse on Linux/macOS; SO_REUSEPORT may not exist everywhere
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except OSError:
                    pass
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.max_buf_size)
            s.bind(("", self.port))  
            if self.multicast_req:
                s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, self.multicast_req)

            s.settimeout(0.2)
            self._stop.clear()
            if IS_PY2:
                self._thread = threading.Thread(target=receive_loop, name=self.__class__.__name__)
                self._thread.setDaemon(True)
            else:
                self._thread = threading.Thread(target=receive_loop, name=self.__class__.__name__, daemon=True)
            self._thread.start()

        except Exception:
            try:
                s.close()
            except Exception:
                pass
            self._sock = None
            raise

    def close(self):
        self._stop.set()
        if self._sock:
            try:
                if self.multicast_req:
                    self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, self.multicast_req)
                self._sock.close()
            except Exception:
                traceback.print_exc()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._sock = None
        self._thread = None
        print(self.__class__.__name__," closed")



    



