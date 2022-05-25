"""Zmq server interface for the OpenAI chatbot"""

import zmq
import sys

if sys.version_info[0] > 2:
    raw_input = input

port = "5556"

class OaiClient:

    def __init__(self, port = 5556):
        self.port = port
        self.context = zmq.Context()

    def connect(self):
        print("Connecting to server...")
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://localhost:%s" % self.port)
        
    def send(self,s, receiveReply=True):
        self.socket.send_string(s)
        if receiveReply:
            return self.socket.recv()

if __name__ == '__main__':
    client = OaiClient()
    client.connect()
    while True:
        s = raw_input('> ')
        if s:
            print('Response:')
            print(client.send(s))
        else:
            break