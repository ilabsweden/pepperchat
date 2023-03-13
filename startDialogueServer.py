# -*- coding: utf-8 -*-

###########################################################
# This is the main startup script for the GPT-3 OpenAI chatbot server.  
#
# Syntax:
#    python3 startDialogueServer.py
#
# Author: Erik Billing, University of Skovde
# Created: June 2022. 
# License: Copyright reserved to the author. 
###########################################################

from oaichat.oaiserver import OaiServer
from optparse import OptionParser


parser = OptionParser()
parser.add_option("--prompt",
    help="Path to propot file.",
    dest="prompt")
parser.set_defaults(prompt='pepper')
  
if __name__ == '__main__':
    (opts, args_) = parser.parse_args()
    server = OaiServer(user='User 1',prompt=opts.prompt + '.prompt')
    server.start()
    try: 
        print('Type an input message to test your chatbot. Type "history" to print dialogue history or "exit" to quit the server.')
        while True:
            s = input('> ')
            if s == 'exit':
                break
            elif s == 'history':
                for line in server.history: print(line)
            elif s == 'reset':
                server.reset()
                print('Dialogue history reset.')
            elif s:
                print(server.respond(s).getText())
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    print('GPT Server closed.')

    