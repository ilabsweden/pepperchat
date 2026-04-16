import threading
import time
import __parentdir
from comm import TranscriptReceiver

def cbk(text):
    def do_async():
        print("Låtsas jobba en stund med: ", text)
        time.sleep(5)
        print("Klar med: ", text)
    threading.Thread(target=do_async, daemon=True).start()
tr = TranscriptReceiver(cbk)
while True:
    time.sleep(1)