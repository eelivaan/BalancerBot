import network, socket, os, machine, select
from machine import Pin
from time import sleep_ms
from wlancredentials import SSID, PASSWORD

with open('status.html', 'r') as f:
    html = f.read()

def GET_response(cmd, param):
    if cmd == 'GET' and param != '/':
        # return contents of the specified file
        file_content = 'N/A'
        with open('.'+param, 'r') as f:
            file_content = f.read()
        return 'text/plain', file_content
    else:
        # list files in pico
        return 'text/html', html % '<br>'.join([f"|- <a href='/{f}'>{f}</a>" for f in os.listdir()])


def WLAN_connect():
    """ Connect to local wireless network for e.g. mpremote access """
    led = Pin("LED", Pin.OUT)
    led.on()

    # connect to newwork
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print('WLAN active')

    print(f'WLAN trying to connect "{SSID}"')
    wlan.connect(SSID, PASSWORD)
    wlan.config(pm = 0xa11140) # Power saving mode off

    # Wait for connection for 10 seconds or fail
    for i in range(10):
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        print('WLAN waiting for connection...')
        led.off()
        sleep_ms(100)
        led.on()
        sleep_ms(900)

    # Handle connection error
    if wlan.status() != 3:
        print('network connection failed')
        led.off()
        return False
    else:
        print('WLAN connected')
        led.on()
        status = wlan.ifconfig()
        print('ip = ' + status[0])
        return True


def WLAN_disconnect():
    """ Disconnect and deactivate WLAN """
    led = Pin("LED", Pin.OUT)
    wlan = network.WLAN(network.STA_IF)

    if wlan.status() == 3:
        wlan.disconnect()
        print('WLAN disconnected')

    wlan.active(False)
    print('WLAN inactive')
    led.off()


def WLAN_startAP():
    return False


def run_tcp_server(port=2323, stopcondition=lambda: False):
    if not WLAN_connect():
        if not WLAN_startAP():
            return

    # start server
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    server_socket = socket.socket()
    server_socket.settimeout(None)  # blocking mode
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(addr)
    server_socket.listen(1)

    print(f"Listening on port {port}")
    server_running = True
    boot_requested = False

    poll = select.poll()
    poll.register(server_socket)

    while server_running and not stopcondition():
        print("Waiting for clients...")

        try:
            # poll incoming clients with 2 second timeout
            can_accept = False
            for res in poll.ipoll(2000):
                if res[0] == server_socket and (res[1] & (select.POLLIN | select.POLLOUT)):
                    can_accept = True
            if not can_accept:
                continue
            #rlist, wlist, errlist = select.select([server_socket], [], [], 1) # type: ignore
        except KeyboardInterrupt as e:
            poll.unregister(server_socket)
            server_socket.close()
            print('Server closed')
            return
        
        try:
            (client, client_addr) = server_socket.accept()
            print("Client connected:", client_addr)
            cl_file = client.makefile('rwb', 0)

            # read request header
            cmd, path = '', ''
            headers = {'content-length': 0, 'content-type': 'text/plain'}
            while True:
                line = cl_file.readline().decode().strip()
                if not line or line == '\r\n':
                    break
                elif ':' in line:
                    key, value = line.lower().split(':', 1)
                    headers[key.strip()] = value.strip()
                else:
                    print(line)
                    cmd, path, _ = line.split(' ', 3)

            # read request body
            print(cmd, path, headers)
            content_length = int(headers['content-length'])
            resp_type, response = 'text/plain', ''

            if content_length > 0:
                if cmd == 'POST':
                    if 'form-data' in headers['content-type']:
                        boundary = cl_file.readline().strip()
                        content_disposition = cl_file.readline().strip()
                        content_type = cl_file.readline().strip()
                        # save content to file
                        with open('.'+path, 'wb') as f:
                            while line := cl_file.readline():
                                if boundary in line:
                                    break
                                f.write(line)
                        response = 'file-ok'
                    elif 'text/plain' in headers['content-type']:
                        cmd = cl_file.read(content_length).decode().strip()
                        print(cmd)
                else:
                    while cl_file.readline(): pass
            
            # send response
            if cmd == 'GET':
                resp_type, response = GET_response(cmd, path)
            elif cmd == 'QUIT':
                server_running = False
                response = 'quit-ok'
            elif cmd == 'BOOT':
                server_running = False
                boot_requested = True
                response = 'boot-ok'

            if cmd in ('GET', 'POST', 'QUIT', 'BOOT'):
                client.send(f'HTTP/1.0 200 OK\r\n'
                            f'Content-type: {resp_type}\r\n'
                            f'Content-length: {len(response)}\r\n'
                            f'Cache-Control: no-cache\r\n'
                            '\r\n')
                client.send(response)
            else:
                client.send('HTTP/1.0 400 Bad Request\r\n\r\n')

            client.close()

        except OSError as e:
            client.close()
            print("Client disconnected")

    poll.unregister(server_socket)
    server_socket.close()
    print('Server closed')
    sleep_ms(2000)
    WLAN_disconnect()

    if boot_requested:
        machine.soft_reset()
#end run_tcp_server


if __name__ == "__main__":
    run_tcp_server(2323)