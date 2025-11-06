from __future__ import print_function
import threading
import time
import __parentdir
import comm

def test_transcript_receiver():
    def onrec(msg):
        print(msg)
    receiver = comm.TranscriptReceiver(onrec)
    while True:
        time.sleep(.1)

def test_state_reporter():
    reporter = comm.RobotStateReporter()
    state = comm.RobotState()
    while True:
        #state.talking = not state.talking
        reporter.report_cur_state(state)
        time.sleep(.5)

def test_state_listener():
    def on_change(state):
        print(state)
    listener = comm.RobotStateListener(on_change)
    while True:
        time.sleep(.1)

def test_state_comm():
    t = threading.Thread(target=test_state_reporter)
    t.setDaemon(True)
    t.start()
    test_state_listener()

test_state_listener()