# -*- coding: utf-8 -*-

###########################################################
# This module implements the main dialogue functionality for Pepper, based on ChatGPT.
#
# Syntax:
#    python scriptname --pip <ip> --pport <port>
#
#    --pip <ip>: specify the ip of your robot (without specification it will use the ROBOT_IP defined below
#
# Author: Mikael Lebram & Erik Billing, University of Skovde based on code from Johannes Bramauer, Vienna University of Technology
# Created: May 30, 2018 and updated spring progressively during in the period 2022-05 to 2024-04. 
# License: MIT
###########################################################

ROBOT_PORT = 9559 # Robot
ROBOT_IP = "pepper.local" # Pepper default

from optparse import OptionParser
import threading
import traceback
from oai_dialogue.comm import RobotStateReporter
import oai_dialogue.pepper_command as pepper_command
import naoqi
import time
import sys, os
import codecs
from naoqi import ALProxy

def start_thread(target):
    t = threading.Thread(target=target)
    t.setDaemon(True)
    t.start()
    return t

def encode(s):
    return codecs.encode(s,'utf-8','ignore')

class ModuleCommandable(naoqi.ALModule):
    def __init__(self, robot_ip, robot_port ):
        naoqi.ALModule.__init__(self, mod_name )
        self.memory = ALProxy("ALMemory", robot_ip, robot_port)
        self.posture = ALProxy("ALRobotPosture", robot_ip, robot_port)
        self.autonomous_life = ALProxy('ALAutonomousLife')
        self.tts = ALProxy("ALTextToSpeech",  robot_ip, robot_port)
        self.aup = ALProxy("ALAnimatedSpeech",  robot_ip, robot_port)
        self.tablet = ALProxy("ALTabletService", robot_ip, robot_port)
        self.audio = ALProxy("ALAudioDevice")

        self.state_reporter = RobotStateReporter()
        self.command_receiver = pepper_command.CommandReceiver(self.on_command)
        self.memory.subscribeToEvent("TouchChanged", self.getName(), "on_touch_changed")
        self.touched = False
        self.running = True
        self.pending_speech = ""
        self.tablet_wifi_config = None # type: pepper_command.ConfigTabletWifi
        self.speech_config = None # type: pepper_command.ConfigSpeech
        def speech_loop():
            while self.running:
                try:
                    if self.pending_speech:
                        data = encode(self.pending_speech)
                        self.pending_speech = ""
                        self.state_reporter.report_talking(True)
                        if self.speech_config and self.speech_config.animated:
                            self.aup.say(data)
                        else:
                            self.tts.say(data)
                    self.state_reporter.report_talking(False)
                except:
                    traceback.print_exc()
                time.sleep(.01)
        start_thread(speech_loop)
    
    def connect_tablet_wifi(self):
        def wait_for_connection(timeout):
            t = time.time()
            while time.time() - t < timeout:
                if self.tablet.getWifiStatus() == "CONNECTED":
                    return True
                time.sleep(.1)
        if wait_for_connection(3):
            return True
        if self.tablet_wifi_config:
            self.tablet.configureWifi(
                self.tablet_wifi_config.security_type.encode("utf-8"), 
                self.tablet_wifi_config.ssid.encode("utf-8"), 
                self.tablet_wifi_config.pwd.encode("utf-8")
            )
            if wait_for_connection(5):
                return True
        print("Tablet wifi not connected. Check credentials.")

    def on_command(self, command):
        try:
            # type: (pepper_command.Command) -> None
            if isinstance(command, pepper_command.Say):
                self.stop_talking()
                self.pending_speech=command.text
            elif isinstance(command, pepper_command.ConfigSpeech):
                if not self.speech_config or self.speech_config.animated != command.animated:
                    if command.animated:
                        self.autonomous_life.setState('solitary')
                        self.autonomous_life.stopAll()
                    else:
                        if self.autonomous_life.getState() != 'disabled':
                            self.autonomous_life.setState('disabled')
                        self.posture.goToPosture('Stand',0.5)
                if not self.speech_config or self.speech_config.language != command.language:
                    print(command.language, self.tts.getLanguage())
                    self.tts.setLanguage(command.language.encode("utf-8"))
                self.speech_config = command

            elif isinstance(command, pepper_command.ConfigAudio):
                self.audio.setOutputVolume(command.output_volume)

            elif isinstance(command, pepper_command.ConfigTabletWifi):
                self.tablet_wifi_config = command
            elif isinstance(command, pepper_command.OpenUrlOnTablet):
                def connect_and_open():
                    if self.connect_tablet_wifi():
                        self.tablet.loadUrl(command.url.encode("utf-8"))
                        self.tablet.showWebview()
                start_thread(connect_and_open)
        except:
            traceback.print_exc()

    def on_touch_changed(self, name, touches):
        touched = any([len(touch) > 1 and touch[1] == True for touch in touches])
        self.state_reporter.report_head_touched(touched)
        if touched:
            self.stop_talking()

   
    def __del__(self):
        self.stop()

    def stop(self):
        self.memory.unsubscribe(self.getName())
        self.running = False
        self.stop_talking()

    def version(self):
        return "1.0"
    
    def stop_talking(self):
        self.pending_speech = ""
        self.tts.stopAll()
        self.state_reporter.report_talking(False)

def main():
    """ Main entry point

    """
    parser = OptionParser()
    parser.add_option("--pip",
        help="Parent broker port. The IP address or your robot",
        dest="pip")
    parser.add_option("--pport",
        help="Parent broker port. The port NAOqi is listening to",
        dest="pport",
        type="int")
    parser.set_defaults(
        pip=ROBOT_IP,
        pport=ROBOT_PORT)

    (opts, args_) = parser.parse_args()
    pip   = opts.pip
    pport = opts.pport

    # We need this broker to be able to construct
    # NAOqi modules and subscribe to other modules
    # The broker must stay alive until the program exists
    myBroker = naoqi.ALBroker("myBroker",
       "0.0.0.0",   # listen to anyone
       0,           # find a free port and use it
       pip,         # parent broker IP
       pport)       # parent broker port

    global mod_name
    mod_name = "modcomm"
    global modcomm
    modcomm = ModuleCommandable(pip, pport)

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        pass
    myBroker.shutdown()

if __name__ == "__main__":
    main()