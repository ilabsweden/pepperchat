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
import os, sys, codecs
from oaichat.oairesponse import OaiResponse

import dotenv
dotenv.load_dotenv()

if sys.version_info[0] < 3:
    raise ImportError('OpenAI Chat requires Python 3')

import openai

openai.api_key = os.getenv('OPENAI_KEY')

class OaiChat:
  def __init__(self,prompt=None):
    self.reset(prompt)

  def reset(self,prompt=None):
      if prompt is None or isinstance(prompt,str):
        self.history = self.loadPrompt(prompt or os.getenv('OPENAI_PROMPTFILE'))
      else:
        self.history = list(prompt)

  def respond(self, inputText):
    self.history.append('\nPerson: ' + inputText)
    response = openai.Completion.create(
      engine="text-davinci-002",
      prompt='\n'.join(self.history) + '\nRobot: ',
      temperature=0.7,
      max_tokens=256,
      top_p=1,
      frequency_penalty=1,
      presence_penalty=0.5
    )
    r = OaiResponse(response)
    self.history.append('Robot: ' + r.getText())
    return r

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
    s = input('> ')
    if s:
      print(chat.history)
      print(chat.respond(s).getText())
    else:
        break