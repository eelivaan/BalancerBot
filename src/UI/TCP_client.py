import socket, sys, os, requests

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
    if inp == 'help':
        print('Available commands:\n'
              '  get [<filename>]                                   Read file from Pico or return the general status document\n'
              '  upload <source filename> [<target filename>]       Send the specified file to Pico\n'
              '  quit                                               Shutdown Pico\n'
              '  boot                                               Restart Micropython, i.e. run main.py\n'
              '  help                                               Display this help\n'
              '  exit                                               Exit this script\n')
        continue
    elif inp == 'exit':
        break

    params = inp.split(' ')
    cmd = params.pop(0).upper()

    # make requests over wifi
    try:
        if cmd == 'GET' and len(params):
            r = requests.get(f"http://{HOST}:{PORT}/{params[0]}")
        elif cmd == 'GET':
            r = requests.get(f"http://{HOST}:{PORT}")
        elif (cmd == 'UPLOAD' or cmd == 'POST') and len(params):
            host_filename = params[0]
            target_filename = params[1] if len(params) > 1 else host_filename
            with open('main/' + host_filename, 'r') as f:
                r = requests.post(f"http://{HOST}:{PORT}/{target_filename}", files={'file': f})
        else:
            r = requests.post(f"http://{HOST}:{PORT}", data=cmd.encode())
    except OSError as e:
        print(RED, 'Error:', e, RESET)
        continue

    # print results
    print(GREEN if r.status_code == 200 else RED, end='')
    print(r.status_code)
    if r.status_code == 200:
        print(GRAY, end='')
        print(r.text)
    print(RESET, end='')

    r.close()
