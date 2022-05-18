from fileinput import filename
import os
import sys
import aiml

if sys.version_info[0] > 2:
    raw_input = input

class Chatbot:

    def __init__(self,db,properties='bot.properties',brain=None,commands=[]):
        self.brain=brain
        self.k = aiml.Kernel()

        if self.brain and os.path.exists(self.brain):
            print("Loading from brain file: " + self.brain)
            self.k.loadBrain(self.brain)
        else:
            self.learn(db,commands)
            if self.brain:
                print("Saving brain file: " + self.brain)
                self.k.saveBrain(self.brain)

        if properties: 
            for p,v in self.loadProperties(properties).items():
                self.k.setBotPredicate(p,v)

    def learn(self,path,commands=[]):
        if os.path.isdir(path):
            for dirpath,dirnames,filenames in os.walk(path):
                for f in filenames:
                    if f.endswith('.aiml'):
                        self.learn(os.path.join(dirpath,f))
        elif os.path.isfile(path):
            print("Learning from",path)
            self.k.bootstrap(learnFiles=path,commands=commands)
        else:
            print('Chatbot: Specified path does not exist:',path)

    def respond(self,inputText):
        return self.k.respond(inputText)

    def loadProperties(self,filepath, sep='=', comment_char='#'):
        """
        Read the file passed as parameter as a properties file.
        """
        props = {}
        with open(filepath, "rt") as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith(comment_char):
                    key_value = l.split(sep)
                    key = key_value[0].strip()
                    value = sep.join(key_value[1:]).strip().strip('"')
                    if value:
                        props[key] = value 
        return props

if __name__ =='__main__':
    chatbot = Chatbot('julia.aiml', brain=None)
    while True:
        input_text = raw_input("> ")
        response = chatbot.respond(input_text)
        print(response)