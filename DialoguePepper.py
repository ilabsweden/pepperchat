# This is a Py-script version of the Dialouge-Pepper.ipynb notebook

#It has been used python 2.7.18, the cell will give you your current verison.
import sys
print("Python version:")
print (sys.version)

#--

import subprocess
from subprocess import Popen, PIPE, STDOUT

pobj = subprocess.Popen(['java', '-jar', 'lib/Ab.jar', 'Main', 'bot=en'],
                            stdin =subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

#-- import subprocess as sp
from threading import Thread
from Queue import Queue,Empty
import time

def getabit(o,q):
    for c in iter(lambda:o.read(1),b''):
        q.put(c)
    o.close()

def getdata(q):
    r = b''
    while True:
        try:
            c = q.get(False)
        except Empty:
            break
        else:
            r += c
    return r



q = Queue()
t = Thread(target=getabit,args=(pobj.stdout,q))
t.daemon = True
t.start()

while True:
    print('Sleep for 2 seconds...')
    time.sleep(2)#to ensure that the data will be processed completely
    print('Data received:' + getdata(q).decode())
    if not t.isAlive():
        break
    #in_dat = input('Your data to input:')
    pobj.stdin.write(b'hello\n')
    #when human says nothing
    #pobj.stdin.write(b'\n')
    pobj.stdin.flush()
    break
    
#--

print('DATA RECEIVED:\n' + getdata(q).decode())

# --

def processResponse(raw):
    response = raw.replace("\n", " ") # changes new-line with space 
    #response = response[7:-7]  # cuts beginning and end
    temp = response.partition('Robot:')[-1].rpartition('Human:')[0] #takes response between "Robot:" and "Human:"
    if not temp:
        return response
    return temp

#--

#test
classic_response = "Robot: Hi nice to see you! \nHuman: "
error_response = "[Error string lenght can vary] Robot: I don't have an answer for that. \nHuman: "
print '-----RAW:-----'
print error_response
print '-----PROCESSED:-----'
print processResponse(error_response)
