# Should be kept useable by python2
UDP_PORT = 50006
UDP_IP = "224.1.1.6"
import udp
class TranscriptSender(udp.UdpSender):
    def __init__(self):
        super().__init__(UDP_PORT, UDP_IP)
    def send(self, transcript):
        # type: (str) -> None
        print("skickar")
        self.send_data(transcript.encode("utf-8"))

class TranscriptReceiver(udp.UdpReceiver):
    def __init__(self, callback):
        # type: (callable[[str], None]) -> TranscriptReceiver
        def cbck(data):
            callback(data.decode("utf-8"))
        super().__init__(cbck, UDP_PORT, UDP_IP)
        self.start()