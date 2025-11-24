from __future__ import print_function
import threading
import time

import numpy as np
import __parentdir
import comm

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


def test_command_sender():
    sender = pepper_command.CommandSender()
    while True:
        time.sleep(.5)
        sender.send(pepper_command.ConfigSpeech("se",True))

def test_command_receiver():
    def rec(cmd):
        print(cmd.__dict__)
    receiver = pepper_command.CommandReceiver(rec)
    while True:
        time.sleep(.5)

def test_command_both():
    threading.Thread(target=test_command_receiver,daemon=True).start()
    test_command_sender()

pepper_command.CommandSender().send(pepper_command.Say("Hey!"))
time.sleep(1)