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

import functools
from optparse import OptionParser
import re
import threading
import traceback
from micke.comm import TranscriptReceiver, RobotStateReporter
import naoqi
import time
import sys, os
import codecs
from naoqi import ALProxy

import dotenv
dotenv.load_dotenv()

OPENAI_PROMPTFILE = os.getenv('OPENAI_PROMPTFILE','dialogue.prompt')
START_PROMPT = codecs.open(OPENAI_PROMPTFILE,encoding='utf-8').read() if os.path.isfile(OPENAI_PROMPTFILE) else ''
#participantId = raw_input('Participant ID: ')
#ALIVE = int(participantId) % 2 == 1
ALIVE = True
class DummyChatbot:
    def respond(self, msg):
        return codecs.encode(msg,'utf8','ignore') if isinstance(msg,str) else msg
    

class SpeakModule(naoqi.ALModule):
   
    def __init__( self, strModuleName, strNaoIp ):
        self.misunderstandings=0
        self.log = codecs.open('dialogue.log','a',encoding='utf-8')
        try:
            naoqi.ALModule.__init__(self, strModuleName )
            self.BIND_PYTHON( self.getName(),"callback" )
            self.strNaoIp = strNaoIp
            #self.session = qi.Session()
        except(BaseException, err):
            print( "ERR: " + self.__class__.__name__  + ": loading error:" + str(err))
 
    def __del__(self):
        print( "INF:" + self.__class__.__name__ + ".__del__: cleaning everything" )
        self.stop()

    def start(self):
        self.memory = naoqi.ALProxy("ALMemory", self.strNaoIp, ROBOT_PORT)
        self.configureTextToSpeech()
        self.state_reporter = RobotStateReporter()
        self.transcript_receiver = TranscriptReceiver(self.handle_input_message)
        #self.touch = ALProxy("ALTouch", self.strNaoIp, ROBOT_PORT)
        self.memory.subscribeToEvent("TouchChanged", self.getName(), "on_touch_changed")
        self.touched = False
        tablet = ALProxy("ALTabletService", self.strNaoIp, ROBOT_PORT)

        try:
            #tablet.configureWifi("wpa", "ShcRobots", "pepperoni")
            t = time.time()
            print("Connecting...")
            while tablet.getWifiStatus() != "CONNECTED" and time.time() - t < 5:
                time.sleep(.1)
            print(tablet.getWifiStatus())
            print("loadurl:", tablet.loadUrl("http://192.168.2.114:8088/subtitles.html?t="+str(int(time.time()))))
            print("showwv:", tablet.showWebview())

        except Exception as e:
            print("Error:", e)        

    def on_touch_changed(self, name, touches):
        touched = False
        for touch in touches:
            touched = touched or (len(touch) > 1 and touch[1] == True)
        if touched != self.touched:
            self.touched = touched
            self.state_reporter.report_head_touched(touched)
            if touched:
                self.stop_talking()

   
    def stop(self):
        print( "INF: " + self.__class__.__name__ + ": stopping..." )
        self.memory.unsubscribe(self.getName())
        print( "INF: " + self.__class__.__name__ + ": stopped!" )

    def version(self):
        return "1.0"

    def configureTextToSpeech(self):
        try:
            self.posture = ALProxy("ALRobotPosture", self.strNaoIp, ROBOT_PORT)
            self.tts = ALProxy("ALTextToSpeech",  self.strNaoIp, ROBOT_PORT)
            if ALIVE:
                self.aup = ALProxy("ALAnimatedSpeech",  self.strNaoIp, ROBOT_PORT)
            else:
                self.aup = self.tts
        except RuntimeError:
            print ("Can't connect to Naoqi at ip \"" + self.strNaoIp + "\" on port " + str(ROBOT_PORT) +".\n"
               "Please check your script arguments. Run with -h option for help.")
        
        self.tts.setLanguage(os.getenv('LANGUAGE_PEPPER'))
        print(self.tts.getLanguage())

    def encode(self,s):
        return codecs.encode(s,'utf-8','ignore')

    def say_string(self, text):
        self.state_reporter.report_talking(True)
        self.aup.say(self.encode(text))
        self.state_reporter.report_talking(False)
    
    def stop_talking(self):
        print("Stop talking!")
        self.tts.stopAll()
        self.state_reporter.report_talking(False)

    def handle_input_message(self, message):
        # type: (str) -> None
        self.log.write('INP: ' + message + '\n')
        print("Message: " + message)
        if message == "stfu":
            self.stop_talking()
            return
        self.say_string(message)

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


    MODULE_NAME = "speakModule"
    try:
        p = ALProxy(MODULE_NAME)
        p.exit()  # kill previous instance
    except:
        pass

    audio = ALProxy("ALAudioDevice")
    audio.setOutputVolume(70)

    Dialog = ALProxy('ALDialog')
    Dialog.stopDialog()
    Dialog.deactivateTopic('all')

    AutonomousLife = ALProxy('ALAutonomousLife')
    RobotPosture = ALProxy('ALRobotPosture')
    if ALIVE:
        AutonomousLife.setState('solitary')
        AutonomousLife.stopAll()
        #AutonomousLife.switchFocus('julia-8b4016/behavior_1')
        print('Odd participant number, autonomous life enabled.')
    else:
        if AutonomousLife.getState() != 'disabled':
            AutonomousLife.setState('disabled')
        RobotPosture.goToPosture('Stand',0.5)
        print('Even participant number, autonomous life disabled.')

   
    # Reinstantiate module

    # Warning: must be a global variable
    # The name given to the constructor must be the name of the
    # variable
    global speakModule
    speakModule = SpeakModule(MODULE_NAME, pip)
    speakModule.start()

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