import socket, sys, os, requests

# change cwd one level up
os.chdir(os.path.dirname(os.path.abspath(__file__)) + os.sep + '..')

HOST = sys.argv[1]
PORT = int(sys.argv[2])
GREEN = '\033[92m'
GRAY = '\033[90m'
RESET = '\033[0m'

while True:
    inp = input('> ')
    if not inp:
        continue
    if 'help' in inp:
        print('Available commands:\n'
              '  GET /\n'
              '  upload <host filename> [<target filename>]\n'
              '  quit\n'
              '  help\n')
        continue

    params = inp.split(' ')
    cmd = params.pop(0).upper()

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

    print(GREEN, end='')
    print(r.status_code)
    if r.status_code == 200:
        print(GRAY, end='')
        print(r.text)
    print(RESET, end='')

    r.close()
