# -*- coding: utf-8 -*-

###########################################################
# This module implements the main dialogue functionality for Pepper, based on ChatGPT.
#
# Syntax:
#    python scriptname --pip <ip> --pport <port>
#
#    --pip <ip>: specify the ip of your robot (without specification it will use the ROBOT_IP defined below
#
# Author: Erik Billing, University of Skovde based on code from Johannes Bramauer, Vienna University of Technology
# Created: May 30, 2018 and updated spring progressively during in the period 2022-05 to 2024-04. 
# License: MIT
###########################################################

ROBOT_PORT = 9559 # Robot
ROBOT_IP = "pepper.local" # Pepper default

from optparse import OptionParser
import re
import threading
import traceback
from micke.comm import RobotStateReporter
import micke.pepper_command as pepper_command
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

class ModuleCommandable(naoqi.ALModule):
    def __init__( self, strModuleName, strNaoIp ):
        try:
            naoqi.ALModule.__init__(self, strModuleName )
            self.BIND_PYTHON( self.getName(),"callback" )
            self.strNaoIp = strNaoIp
        except(BaseException, err):
            print( "ERR: " + self.__class__.__name__  + ": loading error:" + str(err))


    def __del__(self):
        print( "INF:" + self.__class__.__name__ + ".__del__: cleaning everything" )
        self.stop()

    def start(self):
        self.memory = ALProxy("ALMemory", self.strNaoIp, ROBOT_PORT)
        self.posture = ALProxy("ALRobotPosture", self.strNaoIp, ROBOT_PORT)
        self.autonomous_life = ALProxy('ALAutonomousLife')
        self.tts = ALProxy("ALTextToSpeech",  self.strNaoIp, ROBOT_PORT)
        self.aup = ALProxy("ALAnimatedSpeech",  self.strNaoIp, ROBOT_PORT)
        self.tablet = ALProxy("ALTabletService", self.strNaoIp, ROBOT_PORT)
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
                        data = self.encode(self.pending_speech)
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
                self.tablet_wifi_config.security_type, 
                self.tablet_wifi_config.ssid, 
                self.tablet_wifi_config.pwd
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
                    self.tts.setLanguage(command.language)
                self.speech_config = command

            elif isinstance(command, pepper_command.ConfigAudio):
                self.audio.setOutputVolume(command.output_volume)

            elif isinstance(command, pepper_command.ConfigTabletWifi):
                self.tablet_wifi_config = command
            elif isinstance(command, pepper_command.OpenUrlOnTablet):
                def connect_and_open():
                    if self.connect_tablet_wifi():
                        self.tablet.loadUrl(command.url)
                        self.tablet.showWebview()
                start_thread(connect_and_open)
        except:
            traceback.print_exc()

    def on_touch_changed(self, name, touches):
        touched = any([len(touch) > 1 and touch[1] == True for touch in touches])
        self.state_reporter.report_head_touched(touched)
        if touched:
            self.stop_talking()

   
    def stop(self):
        print( "INF: " + self.__class__.__name__ + ": stopping..." )
        self.memory.unsubscribe(self.getName())
        self.running = False
        self.stop_talking()
        print( "INF: " + self.__class__.__name__ + ": stopped!" )

    def version(self):
        return "1.0"

    def encode(self,s):
        return codecs.encode(s,'utf-8','ignore')
    
    def stop_talking(self):
        self.pending_speech = ""
        self.tts.stopAll()
        self.state_reporter.report_talking(False)

    def react(self,s):
        if re.match(".*I.*sit down.*",s): # Sitting down
            self.posture.goToPosture("Sit",1.0)
        elif re.match(".*I.*stand up.*",s): # Standing up
            self.posture.goToPosture("Stand",1.0)
        elif re.match(".*I.*(lie|lyi).*down.*",s): # Lying down
            self.posture.goToPosture("LyingBack",1.0)

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


    MODULE_NAME = "moduleCommandable"
    try:
        p = ALProxy(MODULE_NAME)
        p.exit()  # kill previous instance
    except:
        pass


    Dialog = ALProxy('ALDialog')
    Dialog.stopDialog()
    Dialog.deactivateTopic('all')

    # Reinstantiate module

    # Warning: must be a global variable
    # The name given to the constructor must be the name of the
    # variable
    global moduleCommandable
    moduleCommandable = ModuleCommandable(MODULE_NAME, pip)
    moduleCommandable.start()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print
        print("Interrupted by user, shutting down")
        myBroker.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()