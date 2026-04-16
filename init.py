
env = '.env'
print('Initiating PepperChat environment in %s'%env)

import os, sys

DEFAULTS = {
    'LOGDIR': 'logs',
    'OPENAI_KEY': '',
    'LANGUAGE': 'English',
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
