"""Zmq server interface for the OpenAI chatbot"""

import zmq
import time
import sys

port = "5556"

class OaiServer:

    def __init__(self, port = 5556):
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:%d"%self.port)

    def listen(self):
        #  Wait for next request from client
        return self.socket.recv()

    def send(self,s):
        return self.socket.send_string(s)

if __name__ == '__main__':
    server = OaiServer()
    while True:
        print("Received request: ", server.listen())
        time.sleep(1)  
        server.send("World from OpenAI")