# -*- coding: utf-8 -*-

###########################################################
# OaiResponse class definition.   
#
# Author: Erik Billing, University of Skovde
# Created: June 2022. 
# License: Copyright reserved to the author. 
###########################################################
import json

class OaiResponse:

  def __init__(self, response):
    self.json = json.loads(response) if isinstance(response,str) else response

  def getText(self):
    return self.json['choices'][0]['text'].strip()