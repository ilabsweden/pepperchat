
import json
import sys

if len(sys.argv) < 2:
    print('Please specify log file to be printed.')
else:
    with open(sys.argv[1]) as f:
        s = '[' + f.read()[:-2] + ']'
        for i in json.loads(s):
            if 'receiving' in i and 'choices' in i['receiving']:
                print('P: ' + i['receiving']['choices'][0]['text'].strip())
            if 'sending' in i and 'input' in i['sending']:
                print('H: ' + i['sending']['input'].strip())
        

