
env = '.env'
print('Initiating PepperChat environment in %s'%env)

import os, sys

DEFAULTS = {
    'LOGDIR': 'logs',
    'OPENAI_PROMPTFILE': 'openai.prompt',
    'CHATBOT_SERVER_ADDRESS': 'tcp://localhost:5556'
}

if sys.version_info[0] > 2:
    raw_input = input

if os.path.isfile(env):
    print('%s already exists, exiting.'%env)
else:
    DEFAULTS['OPENAI_KEY'] = raw_input('Specify your OpenAI account key >')

    with open(env,'w') as f: 
        for key, value in DEFAULTS.items():
            f.write('%s=%s\n'%(key,value))
    print('Done. Default environment stored in %s.'%env)
