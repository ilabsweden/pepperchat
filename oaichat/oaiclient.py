# -*- coding: utf-8 -*-
"""Zmq server interface for the OpenAI chatbot"""

import zmq
import sys
import json
from oairesponse import OaiResponse

if sys.version_info[0] > 2:
    raw_input = input

port = "5556"

class OaiClient:

    def __init__(self, history=(), port=5556):
        
        self.port = port
        self.context = zmq.Context()

        print("Connecting to server...")
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://localhost:%s" % self.port)
        if history:
            print('Updating hiostory...',self.send({'history':history,'reset':True}))

    def respond(self,s):
        return OaiResponse(self.send({'input':s})).getText()

    def send(self,o):
        self.socket.send_string(json.dumps(o))
        return json.loads(self.socket.recv())

if __name__ == '__main__':
    client = OaiClient(('Your name is Pepper.','We are currently at the Interaction Lab in Skovde, Sweden.','You are a robot.'))
    while True:
        s = raw_input('> ')
        if s:
            print('Response: ' + client.respond(s).getText())
        else:
            break