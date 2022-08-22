# -*- coding: utf-8 -*-

###########################################################
# This module implements the main dialogue functionality for Pepper. 
#
# Syntax:
#    python logprint.py <path to log file>
#
# Author: Erik Billing, University of Skovde
# Created: June 2022. 
# License: MIT
###########################################################

import json
import sys
from datetime import datetime

if len(sys.argv) < 2:
    print('Please specify log file to be printed.')
else:
    with open(sys.argv[1]) as f:
        s = '[' + f.read()[:-2] + ']'
        lastt = None
        for i in json.loads(s):
            t = datetime.strptime(i['receiving']['time'] if 'receiving' in i else i['sending']['time'],'%Y-%m-%dT%H:%M:%S.%f')
            if lastt:
                d = t-lastt
                print('Replied in %.1f seconds.'%d.total_seconds())
            else:
                print('Conversation started ' + str(t))
            lastt = t


            if 'receiving' in i and 'choices' in i['receiving']:
                print('P: ' + i['receiving']['choices'][0]['text'].strip())
            if 'sending' in i and 'input' in i['sending']:
                print('H: ' + i['sending']['input'].strip())
        

