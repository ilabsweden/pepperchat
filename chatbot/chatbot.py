import os
import sys
import aiml

if sys.version_info[0] > 2:
    raw_input = input

class Chatbot:

    def __init__(self,aimlPath="std-startup.aiml",brainPath="brain.dump"):
        self.brain=brainPath
        self.k = aiml.Kernel()

        if os.path.exists(self.brain):
            print("Loading from brain file: " + self.brain)
            self.k.loadBrain(self.brain)
        else:
            print("Parsing aiml files")
            self.k.bootstrap(learnFiles=aimlPath, commands="load aiml b")
            print("Saving brain file: " + self.brain)
            self.k.saveBrain(self.brain)

    def respond(self,inputText):
        return self.k.respond(inputText)

if __name__ =='__main__':
    chatbot = Chatbot()
    while True:
        input_text = raw_input("> ")
        response = chatbot.respond(input_text)
        print(response)