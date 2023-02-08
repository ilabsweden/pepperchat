# -*- coding: utf-8 -*-

###########################################################
# The GPT-3 OpenAI chatbot class definition. Executes a local
# text based chatbot interface using the GPT-3 chatbot. 
#
# Syntax:
#    python3 openaichat.py
#
# Author: Erik Billing, University of Skovde
# Created: June 2022. 
# License: Copyright reserved to the author. 
###########################################################
import os, sys, codecs, json
from datetime import datetime
from threading import Thread
from oaichat.oairesponse import OaiResponse

import dotenv
dotenv.load_dotenv()

if sys.version_info[0] < 3:
    raise ImportError('OpenAI Chat requires Python 3')

import openai

openai.api_key = os.getenv('OPENAI_KEY')

class OaiChat:
  def __init__(self,user,prompt=None):
    self.log = None
    self.reset(user,prompt)

  def reset(self,user,prompt=None):
    self.user = user
    if prompt is None or isinstance(prompt,str):
      self.history = self.loadPrompt(prompt or os.getenv('OPENAI_PROMPTFILE'))
    else:
      self.history = list(prompt)
    self.resetRequestLog()

  def resetRequestLog(self):
    if (self.log): self.log.close()
    logdir = os.getenv('LOGDIR')
    if not os.path.isdir(logdir): os.mkdir(logdir)
    log = 'requests.%s.%s.log'%(self.user,datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    self.log = open(os.path.join(logdir,log),'a')
    print('Logging requests to',log)

  def respond(self, inputText):
    start = datetime.now()
    self.moderation = None
    #moderator = Thread(target=self.getModeration,args=(inputText,))
    #moderator.start()
    self.history.append('\nPerson: ' + inputText)
    response = self.getCompletion(
      engine="text-davinci-003",
      user=self.user,
      prompt='\n'.join(self.history) + '\nRobot: ',
      temperature=0.7,
      max_tokens=256,
      top_p=1,
      frequency_penalty=1,
      presence_penalty=0
    )
    #moderator.join()
    #print('Moderation:',self.moderation)
    r = OaiResponse(response)

    self.history.append('Robot: ' + r.getText())
    print('Request delay',datetime.now()-start)
    return r

  def getCompletion(self,**kwargs):
    json.dump(kwargs,self.log)
    self.log.write(',\n')
    return openai.Completion.create(**kwargs)

  def loadPrompt(self,promptFile):
    promptFile = promptFile or 'openai.prompt'
    promptPath = promptFile if os.path.isfile(promptFile) else os.path.join(os.path.dirname(__file__),promptFile)
    if not os.path.isfile(promptPath):
      print('WARNING: Unable to locate OpenAI prompt file',promptFile)
      return []
    with codecs.open(promptPath,encoding='utf-8') as f:
      return f.readlines()

if __name__ == '__main__':
  chat = OaiChat()

  while True:
    try:
      s = input('> ')
    except KeyboardInterrupt:
      break
    if s:
      print(chat.history)
      print(chat.respond(s).getText())
    else:
        break
  print('Closing GPT Server')