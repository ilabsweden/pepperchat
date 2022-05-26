
print 'hej'

IP_number = '193.11.99.177'
port_number = 9559

import naoqi
from naoqi import ALProxy
import qi
import os
import time
from random import randint

class BaseSpeechReceiverModule(naoqi.ALModule):
    """
    Use this object to get call back from the ALMemory of the naoqi world.
    Your callback needs to be a method with two parameter (variable name, value).
    """

    def __init__( self, strModuleName ):
        try:
            naoqi.ALModule.__init__(self, strModuleName )
            self.BIND_PYTHON( self.getName(),"callback" )

        except BaseException, err:
            print( "ERR: ReceiverModule: loading error: %s" % str(err) )

    # __init__ - end
    def __del__( self ):
        print( "INF: ReceiverModule.__del__: cleaning everything" )
        self.stop()

    def start( self ):
        memory = naoqi.ALProxy("ALMemory", IP_number, port_number)
        memory.subscribeToEvent("SpeechRecognition", self.getName(), "processRemote")
        print( "INF: ReceiverModule: started!" )


    def stop( self ):
        print( "INF: ReceiverModule: stopping..." )
        memory = naoqi.ALProxy("ALMemory", IP_number, port_number)
        memory.unsubscribe(self.getName())

        print( "INF: ReceiverModule: stopped!" )

    def version( self ):
        return "1.1"

    def processRemote(self, signalName, message):
        # Do something with the received speech recognition result
        print(message)

myBroker = naoqi.ALBroker("myBroker",
   "0.0.0.0",   # listen to anyone
   0,           # find a free port and use it
   IP_number,         # parent broker IP
   port_number)       # parent broker port

try:
    p = ALProxy("BasicSpeechReceiverModule", IP_number, port_number)
    p.exit()  # kill previous instance
    pass
except:
    pass

global BaseSpeechReceiverModule
BaseSpeechReceiverModule = BaseSpeechReceiverModule("BaseSpeechReceiverModule")
BaseSpeechReceiverModule.start()
