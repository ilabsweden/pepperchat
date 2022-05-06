import os
import aiml

BRAIN_FILE="brain.dump"

k = aiml.Kernel()
d = os.path.dirname(__file__)

# To increase the startup speed of the bot it is
# possible to save the parsed aiml files as a
# dump. This code checks if a dump exists and
# otherwise loads the aiml from the xml files
# and saves the brain dump.
if os.path.exists(os.path.join(d,BRAIN_FILE)):
    print("Loading from brain file: " + BRAIN_FILE)
    k.loadBrain(os.path.join(d,BRAIN_FILE))
else:
    print("Parsing aiml files")
    k.bootstrap(learnFiles=os.path.join(d,"std-startup.aiml"), commands="load aiml b")
    print("Saving brain file: " + BRAIN_FILE)
    k.saveBrain(os.path.join(d,BRAIN_FILE))

if __name__ =='__main__':
    # Endless loop which passes the input to the bot and prints
    # its response
    while True:
        input_text = raw_input("> ")
        response = k.respond(input_text)
        print(response)
else:
    print(d)