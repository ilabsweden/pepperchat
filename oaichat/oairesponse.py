# -*- coding: utf-8 -*-

###########################################################
# OaiResponse class definition.   
#
# Author: Erik Billing, University of Skovde
# Created: June 2022. 
# License: Copyright reserved to the author. 
###########################################################
import json
try:
  import openai
except ImportError:
  openai = False

ENABLE_MODERATION = False

class OaiResponse:

  def __init__(self, response):
    self.json = json.loads(response) if isinstance(response,str) else response
    if openai and ENABLE_MODERATION: self.moderation = openai.Moderation.create(input=self.getText())
   
  def flagged(self):
    return hasattr(self,'moderation') and self.moderation['results'][0]['flagged']

  def getText(self):
    if self.flagged():
      return "This conversation is going nowhere."
    else:
      return self.json['choices'][0]['text'].strip()
  
  def flaggedResponse(self):
    #categories = self.json['results'][0]['categories']
    #for key,val in categories.items():
    #  if val:
    #    return self.responses[key]
    if self.flagged():
      return "This conversation is going nowhere."
    
  
   
  