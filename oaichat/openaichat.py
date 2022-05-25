
import os
import openai

with open(os.path.join(os.path.dirname(__file__),'openai.key')) as f: 
  openai.api_key = f.read()

class OaiChat:
  def __init__(self,facts):
      self.history = '\n'.join(facts) + '\n'

  def respond(self, inputText):
    self.history += inputText+'\n'
    response = openai.Completion.create(
      engine="text-davinci-002",
      prompt=self.history,
      temperature=0.7,
      max_tokens=256,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0
    )
    r = OaiResponse(response)
    self.history += r.getText() + '\n'
    return r

class OaiResponse:

  def __init__(self, response):
    for k,v in response.items():
      setattr(self,k,v)

  def getText(self):
    return self.choices[0].text