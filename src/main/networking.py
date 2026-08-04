from machine import Pin
from time import sleep_ms
import network, socket, os
from wlancredentials import SSID, PASSWORD

html = """<!DOCTYPE html>
<html>
    <head>
        <title>Pico Status</title>
        <style>
            html { color-scheme: light dark; font-family: monospace; line-height: 1.5; margin-left: 15px; }
        </style>
    </head>
    <body>
        <h1>Pico Status</h1>
        <div>%s</div>
    </body>
</html>
"""

def respond(cmd, param):
    if cmd == 'GET' and param != '/':
        # return contents of the specified file
        file_content = "N/A"
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


def run_tcp_server(port=2323):
    if not WLAN_connect():
        # put Pico in AP mode
        return

    # start server
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    s = socket.socket()
    s.settimeout(None)  # blocking mode
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    print(f"Listening on port {port}")
    server_running = True

    while server_running:
        print("Waiting for clients...")
        try:
            (client, client_addr) = s.accept()
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
            if content_length > 0:
                if cmd == 'POST':
                    if 'form-data' in headers['content-type']:
                        # save content to file
                        boundary = cl_file.readline().strip()
                        content_disposition = cl_file.readline().strip()
                        content_type = cl_file.readline().strip()
                        with open('.'+path, 'wb') as f:
                            while line := cl_file.readline():
                                if boundary in line:
                                    break
                                f.write(line)
                    else:
                        cmd = cl_file.read(content_length).decode()
                        print(cmd)
                else:
                    while cl_file.readline(): pass
                        
            # send response
            if cmd == 'GET' or cmd == 'POST':
                resp_type, response = respond(cmd, path)
                client.send(f'HTTP/1.0 200 OK\r\n'
                            f'Content-type: {resp_type}\r\n'
                            f'Content-length: {len(response)}\r\n'
                            f'Cache-Control: no-cache\r\n'
                            '\r\n')
                client.send(response)
            else:
                client.send('HTTP/1.0 400 Bad Request\r\n\r\n')

            client.close()

            if cmd == 'QUIT':
                server_running = False

        except OSError as e:
            client.close()
            print("Client disconnected")

    sleep_ms(3000)
    WLAN_disconnect()
#end run_tcp_server


if __name__ == "__main__":
    run_tcp_server(2323)