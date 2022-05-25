
from openaichat import OaiChat

chat = OaiChat(('Your name is Pepper.','We are currently at the Interaction Lab in Skövde, Sweden.','You are a robot.'))

while True:
    s = input('> ')
    if s:
        print(chat.history)
        print(chat.respond(s).getText())
    else:
        break

