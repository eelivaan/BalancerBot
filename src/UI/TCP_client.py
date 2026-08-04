import socket
import sys
import os

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
              '  quit\n'
              '  upload <file>\n'
              '  help\n')
        continue

    params = inp.split(' ')
    cmd = params.pop(0).upper()

    body = ""
    if cmd == "UPLOAD":
        if len(params):
            with open('main/' + params[0], 'r') as f:
                body = f.read()
        else:
            print('Error: filename expected')
            continue

    #s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #s.connect((HOST, PORT))
    with socket.create_connection((HOST, PORT), timeout=5.0) as s:
        print(f"{GREEN}Connected to {HOST}:{PORT}{RESET}")
        #s.sendall(inp.encode() + b'\r\n')
        #s.sendall(b'\r\n')
        #for i in range(1):
        #    data = s.recv(1024)
        #    print(repr(data))

        # request
        s_file = s.makefile('rwb', 0)
        s_file.write(f"{cmd} {' '.join(params)}\r\n".encode())
        s_file.write(b'Content-type: text/plain\r\n')
        s_file.write(f'Content-length: {len(body)}\r\n'.encode())
        s_file.write(b'\r\n')
        s_file.flush()
        if body:
            s_file.write(body.encode())
        s_file.flush()

        # read response
        print(GRAY, end='')
        while line := s_file.readline():
            print(line.decode(), end='')

        print(RESET, end='')

        # close connection
        s.close()
        print(f"{GREEN}Connection closed{RESET}")
        