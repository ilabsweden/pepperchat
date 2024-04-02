# -*- coding: utf-8 -*-

###########################################################
# This is the server interface for the GPT-3 OpenAI chatbot.  
#
# Syntax:
#    python3 oaiserver.py
#
# Author: Erik Billing, University of Skovde
# Created: June 2022. 
# License: Copyright reserved to the author. 
###########################################################
"""Zmq server interface for the OpenAI chatbot"""

import zmq, os
import datetime
from threading import Thread
from oaichat.openaichat import OaiChat

class OaiServer(OaiChat):

    def __init__(self, user, prompt=None):
        super().__init__(user, prompt)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind('tcp://*:'+os.getenv('CHATBOT_SERVER_ADDRESS').split(':')[-1])
        self.thread = None

    def start(self):
        self.thread = Thread(target=self._run)
        self.thread.start()

    def _run(self): 
        print('Starting OpenAI chat server...')
        try:
            while self.thread:
                response = {}
                print('Listening for msg...')
                i = self.listen()
                print('Input received:',i)
                if 'handshake' in i: 
                    print('New client connected:',i['handshake'])
                    response['handshake'] = 'ok'
                if 'reset' in i and i['reset']:
                    print('Resetting history.')
                    self.reset(i['user'])
                    response['reset']='ok'
                if 'history' in i:
                    print('Extending history:')
                    for row in i['history']: 
                        print('\t'+row.strip())
                        self.history.append(row.strip())
                    response['history']='ok'
                if 'input' in i:
                    r = self.respond(i['input'])
                    for k,v in r.json.items():
                        response[k] = v        
                response['time'] = datetime.datetime.now().isoformat()
                print('Sending response:',response)        
                self.send(response)
        except zmq.error.ContextTerminated as e:
            pass
                
    def stop(self):
        #self.socket.close()
        self.thread = None
        #self.log.close()
        self.context.destroy()

    def listen(self):
        #  Wait for next request from client
        return self.socket.recv_json()

    def send(self,s):
        return self.socket.send_json(s)

def main():
    server = OaiServer()
    server.start()
    try: 
        while True:
            i = input('Enter q to quit. > ')
            if i == 'q': break
    finally:
        server.stop()
