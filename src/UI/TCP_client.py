"""
    Terminal app for sending HTTP requests over TCP to Pico
"""
import sys, os, requests

# change cwd one level up to src/
os.chdir(os.path.dirname(os.path.abspath(__file__)) + os.sep + '..') # type: ignore

HOST = sys.argv[1]
PORT = int(sys.argv[2])
GREEN = '\033[92m'
RED = '\033[91m'
GRAY = '\033[90m'
RESET = '\033[0m'

while True:
    inp = input('> ')
    if not inp:
        continue
    elif inp == 'help':
        print('Available commands:\n'
              '  get [<filename>]                                   Read file from Pico or return the general status document\n'
              '  upload <source filename> [<target filename>]       Send the specified file to Pico\n'
              '  upload config                                      Shortcut to send config.json to Pico\n'
              '  quit                                               Shutdown Pico\n'
              '  boot                                               Restart Micropython, i.e. run main.py\n'
              '  ping                                               Test connection\n'
              '  help                                               Display this help\n'
              '  exit                                               Exit this script\n')
        continue
    elif inp == 'exit':
        break

    params = inp.split(' ')
    cmd = params.pop(0).upper()

    # make requests over WLAN
    try:
        if cmd == 'GET' and len(params):
            r = requests.get(f"http://{HOST}:{PORT}/{params[0]}", timeout=5)
        elif cmd == 'GET':
            r = requests.get(f"http://{HOST}:{PORT}")
        elif (cmd == 'UPLOAD' or cmd == 'POST') and len(params):
            if params[0] == 'config':
                host_filename, target_filename = '../UI/config.json', 'config.json'
            else:
                host_filename = params[0]
                target_filename = params[1] if len(params) > 1 else host_filename
            with open('main/' + host_filename, 'r') as f:
                r = requests.post(f"http://{HOST}:{PORT}/{target_filename}", files={'file': f})
        else:
            r = requests.post(f"http://{HOST}:{PORT}", data=cmd.encode(), timeout=5)
    except OSError as e:
        print(RED, 'Error:', e, RESET)
        continue

    # print results
    if r.status_code == 200:
        print(GREEN, '200 OK')
    elif r.status_code == 404:
        print(RED, '404 Not Found')
    else:
        print(RED, '400 Bad Request' if r.status_code == 400 else r.status_code)
    print(GRAY, end='')
    print(r.text)
    print(RESET, end='')

    r.close()
