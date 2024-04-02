# -*- coding: utf-8 -*-

###########################################################
# Retrieve robot audio buffer and do google speech recognition
#
# Syntax:
#    python scriptname --pip <ip> --pport <port>
#
#    --pip <ip>: specify the ip of your robot (without specification it will use the ROBOT_IP defined below)
#
# Author: Johannes Bramauer, Vienna University of Technology and Erik Billing, University of Skovde
# Created: May 30, 2018 and updated spring 2022. 
# License: MIT
###########################################################
###########################################################

ROBOT_IP = "pepper.local" # default, for running on Pepper
ROBOT_PORT = 9559

import sys, time
import naoqi
from optparse import OptionParser
from pepperspeechrecognition import SpeechRecognitionModule

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

    try:
        p = ALProxy("SpeechRecognition")
        p.exit()  # kill previous instance, useful for developing ;)
    except:
        pass

    # Reinstantiate module

    # Warning: SpeechRecognition must be a global variable
    # The name given to the constructor must be the name of the
    # variable
    global SpeechRecognition
    SpeechRecognition = SpeechRecognitionModule("SpeechRecognition", pip, pport)

    # uncomment for debug purposes
    # usually a subscribing client will call start() from ALProxy
    #SpeechRecognition.start()
    #SpeechRecognition.startRecording()
    #SpeechRecognition.calibrate()
    #SpeechRecognition.enableAutoDetection()
    #SpeechRecognition.startRecording()

    print('Speech recognition running.')

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
