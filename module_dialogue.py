# -*- coding: utf-8 -*-

###########################################################
# This module implements the main dialogue functionality for Pepper. 
#
# Syntax:
#    python scriptname --pip <ip> --pport <port>
#
#    --pip <ip>: specify the ip of your robot (without specification it will use the NAO_IP defined below
#
# Author: Johannes Bramauer, Vienna University of Technology
# Created: May 30, 2018
# License: MIT
###########################################################

# NAO_PORT = 65445 # Virtual Machine
NAO_PORT = 9559 # Robot

# NAO_IP = "127.0.0.1" # Virtual Machine
NAO_IP = "nao.local" # Pepper default

AUTODEC = True

from optparse import OptionParser
import naoqi
import time
import sys
from naoqi import ALProxy

#from chatbot import Chatbot
#chatbot = Chatbot('std-startup.aiml',commands='load aiml b')

from oaichat import OaiClient
chatbot = OaiClient(('Your name is Pepper.','We are currently at the Interaction Lab in Skövde, Sweden.','You are a robot.'))

class DialogueSpeechReceiverModule(naoqi.ALModule):
    """
    Use this object to get call back from the ALMemory of the naoqi world.
    Your callback needs to be a method with two parameter (variable name, value).
    """
    
    
    def __init__( self, strModuleName, strNaoIp ):
        self.autodec = AUTODEC 
        self.misunderstandings=0
        self.log = open('dialogue.log','a')
        try:
            naoqi.ALModule.__init__(self, strModuleName )
            self.BIND_PYTHON( self.getName(),"callback" )
            self.strNaoIp = strNaoIp
            #self.session = qi.Session()
        except BaseException, err:
            print( "ERR: ReceiverModule: loading error: %s" % str(err) )
 
    def __del__( self ):
        print( "INF: ReceiverModule.__del__: cleaning everything" )
        self.stop()

    def start( self ):
        self.memory = naoqi.ALProxy("ALMemory", self.strNaoIp, NAO_PORT)
        self.memory.subscribeToEvent("SpeechRecognition", self.getName(), "processRemote")
        print( "INF: ReceiverModule: started!" )
        try:
            #self.session.connect("tcp://" + self.strNaoIp + ":" + str(NAO_PORT))
            #self.aup = self.session.service("ALAnimatedSpeech")
            self.aup = ALProxy("ALAnimatedSpeech",  self.strNaoIp, NAO_PORT)
            #self.tts = self.session.service("ALTextToSpeech")
        except RuntimeError:
            print ("Can't connect to Naoqi at ip \"" + self.strNaoIp + "\" on port " + str(NAO_PORT) +".\n"
               "Please check your script arguments. Run with -h option for help.")

    def stop( self ):
        print( "INF: ReceiverModule: stopping..." )
        self.memory.unsubscribe(self.getName())
        print( "INF: ReceiverModule: stopped!" )

    def version( self ):
        return "2.0"

    def processRemote(self, signalName, message):
        self.log.write('INP: ' + message + '\n')
        if message == 'error': 
            print('Input not recognized, continue listen')
            return
        if self.autodec:
            #always disable to not detect its own speech
            SpeechRecognition.disableAutoDetection()
            #and stop if it was already recording another time
            SpeechRecognition.pause()
        # received speech recognition result
        print("INPUT RECOGNIZED: \n"+message)
        #computing answer
        if message=='error':
            self.misunderstandings +=1
            if self.misunderstandings ==1:
                answer="I didn't understand, can you repeat?"
            elif self.misunderstandings == 2:
                answer="Sorry I didn't get it, can you say it one more time?"
            elif self.misunderstandings == 3:
                answer="Today I'm having troubles uderstanding what you are saying, I'm sorry"
            else:
                answer="Please repeat that."
            print('ERROR, DEFAULT ANSWER:\n'+answer)
        else:
            self.misunderstandings = 0
            answer = str(chatbot.respond(message))
            print('DATA RECEIVED AS ANSWER:\n'+answer)
        #text to speech the answer
        self.log.write('ANS: ' + answer + '\n')
        self.aup.say(answer)
        #time.sleep(2)
        if self.autodec:
            print("starting service speech-rec again")
            SpeechRecognition.start()
            print("autodec enabled")
            SpeechRecognition.enableAutoDetection()
        else:
            #asking the Speech Recognition to LISTEN AGAIN
            SpeechRecognition.startRecording()

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
        pip=NAO_IP,
        pport=NAO_PORT)

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



    try:
        p = ALProxy("DialogueSpeechReceiver")
        p.exit()  # kill previous instance
    except:
        pass

    #AutonomousLife = ALProxy('ALAutonomousLife')
    #AutonomousLife.setState('solitary')

    # Reinstantiate module

    # Warning: ReceiverModule must be a global variable
    # The name given to the constructor must be the name of the
    # variable
    global DialogueSpeechReceiver
    DialogueSpeechReceiver = DialogueSpeechReceiverModule("DialogueSpeechReceiver", pip)
    DialogueSpeechReceiver.start()

    global SpeechRecognition
    SpeechRecognition = ALProxy("SpeechRecognition")
    SpeechRecognition.start()
    #SpeechRecognition.calibrate()

    if(AUTODEC==False):
        print("False, auto-detection not available")
        #one-shot recording for at least 5 seconds
        SpeechRecognition = ALProxy("SpeechRecognition")
        SpeechRecognition.start()
        SpeechRecognition.setHoldTime(5)
        SpeechRecognition.setIdleReleaseTime(1.7)
        SpeechRecognition.setMaxRecordingDuration(10)
        SpeechRecognition.startRecording()

    else:
        print("True, auto-detection selected")
        # auto-detection
        SpeechRecognition = ALProxy("SpeechRecognition")
        SpeechRecognition.start()
        SpeechRecognition.setHoldTime(2.5)
        SpeechRecognition.setIdleReleaseTime(1.0)
        SpeechRecognition.setMaxRecordingDuration(10)
        SpeechRecognition.setLookaheadDuration(0.5)
        #SpeechRecognition.setLanguage("de-de")
        #SpeechRecognition.calibrate()
        SpeechRecognition.setAutoDetectionThreshold(10)
        SpeechRecognition.enableAutoDetection()
        #SpeechRecognition.startRecording()

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