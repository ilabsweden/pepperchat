
################### Adjusting IP and ports ###########################
IP_number = "172.20.10.10" #this is local one, use the real robot ip
port_number = 9559 #this is local one, use the real robot port number

#IMPORTS
import naoqi
from naoqi import ALProxy
import qi
import os
import time
from random import randint

#SESSION OPENING
session = qi.Session()
try:
    session.connect("tcp://" + IP_number + ":" + str(port_number))
except RuntimeError:
    print ("Can't connect to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) +".\n"
               "Please check your script arguments. Run with -h option for help.")
    sys.exit(1)
