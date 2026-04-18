
env = '.env'
print('Initiating PepperChat environment in %s'%env)

import os, sys

DEFAULTS = {
    'LOGDIR': 'logs',
    'OPENAI_KEY': '',
    'LANGUAGE': 'English',
    'DIALOGUE_ENV': 'dialogue.env',
    'TABLET_WIFI_SSID': '',
    'TABLET_WIFI_PWD': '',
    'TABLET_WIFI_SECURITY':'wpa'
}

if sys.version_info[0] > 2:
    raw_input = input

if os.path.isfile(env):
    print('%s already exists, exiting.'%env)
else:
    for key, default in DEFAULTS.items():
        prompt = '%s [%s] >'%(key, default) if default else '%s >'%key
        value = raw_input(prompt).strip()
        if not value:
            value = default
        DEFAULTS[key] = value

    with open(env,'w') as f: 
        for key, value in DEFAULTS.items():
            f.write('%s=%s\n'%(key,value))
    print('Done. Default environment stored in %s.'%env)

    dialogue_env = DEFAULTS['DIALOGUE_ENV']
    if not os.path.isfile(dialogue_env):
        with open(dialogue_env, 'w', encoding='utf-8') as f:
            f.write('PROMPT="I would like you to act as the social robot Pepper.\n')
            f.write('Please respond briefly with one or two sentences."\n\n')
            f.write('SAY="Hello! My name is Pepper, and I am a social robot.\n')
            f.write('It will be great fun to meet you here today!"\n')
        print('Default dialogue stored in %s.'%dialogue_env)
