"""Zmq server interface for the OpenAI chatbot"""

import zmq
import json
from threading import Thread
from openaichat import OaiChat

port = "5556"

class OaiServer(OaiChat):

    def __init__(self, history=(), port=5556):
        super().__init__(history)
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:%d"%self.port)
        self.thread = None

    def start(self):
        self.thread = Thread(target=self._run)
        self.thread.start()

    def _run(self): 
        print('Starting OpenAI chat server...')
        response = {}
        while self.thread:
            i = json.loads(self.listen())
            print('Input received:',i)
            if 'reset' in i and i['reset']:
                self.history = []
                response['reset']='ok'
            if 'history' in i:
                self.history.extend(i['history'])
                response['history']='ok'
            if 'input' in i:
                r = self.respond(i['input'])
                for k,v in r.json.items():
                    response[k] = v        
            print('Sending response:',response)        
            self.send(json.dumps(response))
                
    def stop(self):
        self.socket.close()
        self.thread = None

    def listen(self):
        #  Wait for next request from client
        return self.socket.recv()

    def send(self,s):
        return self.socket.send_string(s)

if __name__ == '__main__':
    server = OaiServer()
    server.start()
    try: 
        while True:
            i = input('Enter q to quit. > ')
            if i == 'q': break
    finally:
        server.stop()
