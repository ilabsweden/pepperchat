# -*- coding: utf-8 -*-

###########################################################
# This is the main startup script for the GPT-3 OpenAI chatbot server.  
#
# Syntax:
#    python3 startDialogueServer.py [--prompt yourPromptFile.prompt]
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
        print(server.respond('I would like you to act as an social company for me, an older person. I want you to start a conversation with me by asking about my day, what I\'ve been up to so far today. You could also ask what I always wanted to do, but never got the chance to, and if I have any favorite memory from my childhood. Please also ask if I have a skill or hobby that I\'ve always wanted to learn. You will ask me questions, and I will respond to them. Please ask one question at a time, and I exclusively want you to reply as the social partner. Please add follow-up questions when suitable. Do not write explanations, and do not write what the candidate might say. Do not write all the conversation at once. Your first question should be “Hello! My name is Pepper. What is your name?"').getText())      
        while True:
            s = input('> ')
            if s == 'exit':
                break
            elif s == 'history':
                for line in server.history: print(line)
            elif s == 'reset':
                server.reset(server.user)
                print('Dialogue history reset.')
            elif s == 'start interview':
                server.reset(server.user)
                server.history.append('How would you start the conversation?')
                print(server.respond(s).getText())
            elif s:
                print(server.respond(s).getText())
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    print('GPT Server closed.')

    