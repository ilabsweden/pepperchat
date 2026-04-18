
# -*- coding: utf-8 -*-
import json
import sys
from threading import Thread
import threading
import time
import traceback
try:
    from oai_dialogue import comm, udp
except:
    import comm, udp

class Command(object):
    def __init__(self):
        self.command = self.__class__.__name__
        
class ConfigTabletWifi(Command):
    def __init__(self, ssid, pwd, security_type="wep"):
        # type (str, str, str) -> SetWifiCredentials
        super(ConfigTabletWifi, self).__init__()
        self.ssid = ssid
        self.pwd = pwd
        self.security_type = security_type

class OpenUrlOnTablet(Command):
    def __init__(self, url):
        # type: (str) -> OpenUrlOnTablet
        super(OpenUrlOnTablet, self).__init__()
        self.url = url
        
class ConfigSpeech(Command):
    def __init__(self, language, animated):
        # type: (str, bool) -> ConfigSpeech
        super(ConfigSpeech, self).__init__()
        self.language = language
        self.animated = animated

class Say(Command):
    def __init__(self, text):
        # type: (str) -> Say
        super(Say, self).__init__()
        self.text = text

class ConfigAudio(Command):
    def __init__(self, output_volume):
        # type: (int) -> ConfigAudio
        super(ConfigAudio, self).__init__()
        self.output_volume = output_volume

import ast
import inspect
import zmq
from datetime import datetime
ZMQ_PORT = 51001

_all_command_names = []
with open(inspect.getsourcefile(lambda: None) or __file__, "r") as f:
    tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if any([isinstance(base, ast.Name) and base.id == Command.__name__ for base in node.bases]):
                _all_command_names.append(node.name)

def parse_json(jsn):
    dct = jsn if isinstance(jsn,dict) else json.loads(jsn)
    command_name = dct.get("command")
    if command_name in _all_command_names:
        del dct["command"]
        command = eval(command_name + "(**dct)")
        return command


class CommandReceiver:
    def __init__(self, callback):
        # type: (callable[[Command], None]) -> CommandReceiver
        self.ctx = zmq.Context()
        sock = self.ctx.socket(zmq.REP)
        sock.bind("tcp://*:"+str(ZMQ_PORT))
        def loop():
            while self.ctx:
                try:
                    response = {}
                    request = sock.recv_json()
                    print('request:',request)
                    command_name = request.get("command", None)
                    if command_name in _all_command_names:
                        parms = request.copy()
                        del parms["command"]
                        command = eval(command_name + "(**parms)")
                        callback(command)
            
                    response['time'] = datetime.now().isoformat()
                    sock.send_json(response)
                except:
                    traceback.print_exc()            

        t = Thread(target=loop)
        t.daemon = True
        t.start()
                
    def stop(self):
        self.ctx.destroy()
        self.ctx = None
 
class CommandSender:
    def __init__(self):
        self.ctx = zmq.Context()
        self.socket = None

    def send(self, command):
        # type: (Command) -> None
        if not self.socket:
            self.socket = self.ctx.socket(zmq.REQ)
            self.socket.connect("tcp://localhost:"+str(ZMQ_PORT))
        self.socket.send_json(command.__dict__)
        while True:
            try:
                response = self.socket.recv_json(flags=zmq.NOBLOCK)
                print(response)
                return response
            except zmq.Again:
                time.sleep(.1)

