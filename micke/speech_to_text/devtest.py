from __future__ import print_function
import threading
import time

import numpy as np
import pyaudio
import __parentdir
import comm

from transcriber import TranscriberResult
import keyboard
import pepper_command
def test_transcript_receiver():
    def onrec(msg):
        print(msg)
    receiver = comm.TranscriptReceiver(onrec)
    while True:
        time.sleep(.1)

def test_state_reporter():
    reporter = comm.RobotStateReporter()
    talking = False
    while True:
        talking = not talking
        reporter.report_talking(talking)
        time.sleep(.5)

def test_state_listener():
    def on_change(state):
        print(state.__dict__)
    listener = comm.RobotStateListener(on_change)
    while True:
        time.sleep(.1)

def test_state_comm():
    t = threading.Thread(target=test_state_reporter)
    t.setDaemon(True)
    t.start()
    test_state_listener()


def test_command():
    def receiver():
        def rec(cmd):
            print(cmd.__dict__)
        receiver = pepper_command.CommandReceiver(rec)
    
    threading.Thread(target=receiver,daemon=True).start()
    sender = pepper_command.CommandSender()
    ca = pepper_command.ConfigAudio(output_volume=1)
    while True:
        time.sleep(.5)
        ca.output_volume += 1
        sender.send(ca)

test_command()