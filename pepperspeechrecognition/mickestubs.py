from __future__ import print_function
# -*- coding: utf-8 -*-
import os
import sys
import threading
import time


MIC_DEVICE_ID = "Microphone Array on SoundWire D"
MIC_DEVICE_ID = "Mickes tupplurar"


DEFAULT_LANGUAGE = "sv-SE"
spm = None

def get_pyaudio_input_stream(sample_rate, channels, frames_per_buffer):
    import pyaudio
    pa = pyaudio.PyAudio()
    dev_name = pa.get_default_input_device_info().get("name", None)
    dev_idx = None
    for idx in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(idx)
        name = dev.get("name", None) 
        if MIC_DEVICE_ID in name and dev.get("maxInputChannels", 0) > 0:
            dev_idx = idx
            dev_name = name
            break
    return pa.open(
        format=pyaudio.paInt16, 
        channels=channels, 
        rate=sample_rate, 
        input_device_index=dev_idx,
        input=True, 
        frames_per_buffer=frames_per_buffer
    ), dev_name

class ALModule:
    
    def __init__(self, name):
        global spm
        self.name = name
        self.isStarted = False
        print(self.__class__.__name__)
        if self.__class__.__name__ == "SpeechRecognitionModule":
            spm = self
            print(self)
    def BIND_PYTHON(self, a, b):
        pass

    def getName(self):
        return self.name

class ALProxy:
    def __init__(self, name, naoIp="", naoPort=0):
        self.name = name
        self.is_audio_device = name == "ALAudioDevice"
        self.running_mic = False
    def declareEvent(self, evt_name):
        print("declareEvent", evt_name)

    def setClientPreferences(self,a,b,c,d):
        print("setClientPreferences", a, b, c, d)

    def raiseEvent(self, evt_name, data):
        print("raiseEvent",evt_name,data)

    def subscribe(self, name):
        print("subscribe",name)
        self.run_mic()

    def run_mic(self):
        def run():
            self.running_mic = True
            frames_per_buffer = 320
            channels = 2
            stream, _ = get_pyaudio_input_stream(48000, channels, frames_per_buffer)
            try:
                while self.running_mic:
                    pcm = stream.read(frames_per_buffer, exception_on_overflow=False)
                    spm.processRemote(
                        channels, 
                        frames_per_buffer, 
                        str(time.time()).split("."), 
                        pcm 
                    )
            except KeyboardInterrupt:
                pass
            finally:
                stream.stop_stream()
                stream.close()
        thread = threading.Thread(target=run)
        thread.setDaemon(True)
        thread.start()

    def unsubscribe(self, name):
        print("unsubscribe",name)
        self.running_mic = False


