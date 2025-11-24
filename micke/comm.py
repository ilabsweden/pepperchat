# Should be kept useable by python2
import json
import udp

TRANSCRIPT_UDP_PORT = 50006
TRANSCRIPT_UDP_IP = "224.1.1.6"

class TranscriptSender(udp.UdpSender):
    def __init__(self):
        super(TranscriptSender, self).__init__(TRANSCRIPT_UDP_PORT, TRANSCRIPT_UDP_IP)
    def send(self, transcript):
        # type: (str) -> None
        self.send_data(transcript.encode("utf-8"))

class TranscriptReceiver(udp.UdpReceiver):
    def __init__(self, callback):
        # type: (callable[[str], None]) -> TranscriptReceiver
        def cbck(data):
            callback(data.decode("utf-8"))
        super(TranscriptReceiver, self).__init__(cbck, TRANSCRIPT_UDP_PORT, TRANSCRIPT_UDP_IP)
        self.start()


COMMAND_UDP_PORT = 50008
COMMAND_UDP_IP = "224.1.1.8"


ROBOT_STATE_UDP_PORT = 50007
ROBOT_STATE_UDP_IP = "224.1.1.7"

class RobotState:
    def __init__(self):
        self.talking = False
        self.head_touched = False
    def __str__(self):
        return str(self.__dict__)
    
class RobotStateReporter(udp.UdpSender):
    def __init__(self):
        super(RobotStateReporter, self).__init__(ROBOT_STATE_UDP_PORT, ROBOT_STATE_UDP_IP)
        self.state = RobotState()
    def report_cur_state(self):
        # type: (RobotState) -> None
        self.send_data(json.dumps(self.state.__dict__).encode("utf-8"))
    def report_talking(self, t):
        # type: (bool) -> None
        if self.state.talking != t:
            self.state.talking = t
            self.report_cur_state()
    def report_head_touched(self, t):
        # type: (bool) -> None
        if self.state.head_touched != t:
            self.state.head_touched = t
            self.report_cur_state()

class RobotStateListener(udp.UdpReceiver):
    def __init__(self, on_change_callback = None):
        # type: (callable[[RobotState], None]) -> TranscriptReceiver
        self.state = RobotState()
        def cbck(data):
            new_state_dict = json.loads(data.decode("utf-8"))
            state_dict = self.state.__dict__
            changed = False
            for key,val in state_dict.items():
                if key in new_state_dict and val != new_state_dict[key]:
                    state_dict[key] = new_state_dict[key]
                    changed = True
            if changed and on_change_callback:
                on_change_callback(self.state)
        super(RobotStateListener, self).__init__(cbck, ROBOT_STATE_UDP_PORT, ROBOT_STATE_UDP_IP)
        self.start()

