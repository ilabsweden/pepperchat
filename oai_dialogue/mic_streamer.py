from __future__ import print_function

import numpy as np

# -*- coding: utf-8 -*-
###########################################################
# Retrieve robot audio buffer and do google speech recognition
#
# Syntax:
#    python scriptname --pip <ip> --pport <port>
#
#    --pip <ip>: specify the ip of your robot (without specification it will use the NAO_IP defined below)
#
# Author: Johannes Bramauer, Vienna University of Technology. Updated by Erik Billing, University of Skovde, for integration with the OpenAI chatbot.
# Created: May 30, 2018. Updated: November 2022. 
# License: MIT
#
###########################################################

import audio_stream
import naoqi
from naoqi import ALProxy, ALModule
import dotenv
dotenv.load_dotenv()
import traceback

SAMPLE_RATE = 16000         
TRANSCRIPT_UDP_PORT = 50006
TRANSCRIPT_UDP_IP = "224.1.1.6"

class MicStreamerModule(ALModule):
    """
    Use this object to get call back from the ALMemory of the naoqi world.
    Your callback needs to be a method with two parameter (variable name, value).
    """

    def __init__( self, moduleName, naoIp, naoPort=9559):
        try:
            ALModule.__init__(self, moduleName )
            self.BIND_PYTHON( self.getName(),"callback" )
            self.audio_stream_sender = audio_stream.AudioStreamSender(
                sample_rate=SAMPLE_RATE,
                channel_cnt=1, # this will be adjusted in processremote 
                udp_port=audio_stream.DEFAULT_UDP_PORT,
                receiver_ip=audio_stream.DEFAULT_MULTICAST_IP
            )
            self.enabled = True
            self.audio = ALProxy( "ALAudioDevice")
            nNbrChannelFlag = 0 # ALL_Channels: 0,  AL::LEFTCHANNEL: 1, AL::RIGHTCHANNEL: 2 AL::FRONTCHANNEL: 3  or AL::REARCHANNEL: 4.
            nNbrChannelFlag = 3
            nDeinterleave = 0
            self.audio.setClientPreferences( self.getName(),  SAMPLE_RATE, nNbrChannelFlag, nDeinterleave )
            self.audio.subscribe(self.getName())

            

        except BaseException, err:
            print( "ERR: MicStreamerModule: loading error: %s" % str(err) )

    # __init__ - end
    def __del__( self ):
        print( "INF: MicStreamerModule.__del__: cleaning everything" )
        self.stop()

    def enable(self, enable):
        print("INF: MicStreamerModule enabled:",enable)
        self.enabled = enable

    def stop( self ):
        self.enabled = False
        try:
            self.audio.unsubscribe(self.getName())
        except:
            pass
        try:
            self.audio_stream_sender.close()
        except:
            pass
        print("INF: MicStreamerModule: stopped!")

    def processRemote( self, nbOfChannels, nbrOfSamplesByChannel, aTimeStamp, buffer ):
        if self.enabled:
            #print(nbOfChannels, nbrOfSamplesByChannel, len(buffer))
            pcm16bytes = np.fromstring( str(buffer), dtype=np.int16 ).tobytes()
            #pcm16bytes = np.frombuffer(buffer, dtype=np.int16 ).tobytes()
            print(audio_stream.get_peak_bar(nbOfChannels, pcm16bytes))
            self.audio_stream_sender.channel_cnt = nbOfChannels # ensure we got correct number here
            self.audio_stream_sender.send_pcm16_bytes(pcm16bytes)



