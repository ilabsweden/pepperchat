# -*- coding: utf-8 -*-

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
    self.history.append(inputText)
    response = openai.Completion.create(
      engine="text-davinci-002",
      prompt='\n'.join(self.history) + '\n',
      temperature=0.7,
      max_tokens=256,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0
    )
    r = OaiResponse(response)
    self.history.append(r.getText())
    return r

if __name__ == '__main__':
  chat = OaiChat(('Your name is Pepper.','We are currently at the Interaction Lab in Skövde, Sweden.','You are a robot.'))

  while True:
    s = input('> ')
    if s:
      print(chat.history)
      print(chat.respond(s).getText())
    else:
        break