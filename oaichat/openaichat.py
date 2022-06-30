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
import os, sys
from oaichat.oairesponse import OaiResponse

if sys.version_info[0] < 3:
    raise ImportError('OpenAI Chat requires Python 3')

import openai

with open(os.path.join(os.path.dirname(__file__),'openai.key')) as f: 
  openai.api_key = f.read()

class OaiChat:
  def __init__(self,history=()):
      self.history = list(history)

  def respond(self, inputText):
    self.history.append('\nPerson: ' + inputText)
    print('\n'.join(self.history) + '\n')
    response = openai.Completion.create(
      engine="text-davinci-002",
      prompt='\n'.join(self.history) + '\nRobot: ',
      temperature=0.7,
      max_tokens=256,
      top_p=1,
      frequency_penalty=1,
      presence_penalty=0
    )
    r = OaiResponse(response)
    self.history.append('Robot: ' + r.getText())
    return r

if __name__ == '__main__':
  chat = OaiChat()

  while True:
    s = input('> ')
    if s:
      print(chat.history)
      print(chat.respond(s).getText())
    else:
        break