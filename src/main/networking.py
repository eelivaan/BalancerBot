from machine import Pin
from time import sleep_ms
import network, socket, os
from wlancredentials import SSID, PASSWORD

html = """<!DOCTYPE html>
<html>
    <head>
        <title>Pico Status</title>
        <style>
            html { color-scheme: light dark; font-family: monospace; line-height: 1.5; }
        </style>
    </head>
    <body>
        <h1>Pico Status</h1>
        <div>%s</div>
    </body>
</html>
"""

def respond(cmd, param):
    if cmd == 'GET' and param:
        file_content = "N/A"
        with open(param, 'r') as f:
            file_content = f.read()
        return 'text/plain', file_content
    elif cmd == 'quit':
        return 'text/plain', 'quit-ok'
    else:
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
    led = Pin("LED", Pin.OUT)
    wlan = network.WLAN(network.STA_IF)

    if wlan.status() == 3:
        wlan.disconnect()
        print('WLAN disconnected')

    wlan.active(False)
    print('WLAN inactive')
    led.off()


def run_tcp_server(port=2323):
    WLAN_connect()

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
            cmd, param = '', ''
            headers = {'content-length': 0}
            while True:
                line = cl_file.readline()
                if not line or line == b'\r\n':
                    break
                line = line.decode().strip()
                if 'GET' in line:
                    cmd = 'GET'
                    param = line.split(' ')[1][1:]
                elif 'QUIT' in line:
                    cmd = 'quit'
                    server_running = False
                    break
                elif 'UPLOAD' in line:
                    cmd = 'upload'
                    param = line.split(' ')[1]
                elif ':' in line:
                    key, value = line.lower().split(':', 1)
                    headers[key.strip()] = value.strip()
            # read request body
            body_length = int(headers['content-length'])
            if body_length > 0:
                body = cl_file.read(body_length)
                if cmd == 'upload':
                    with open(param, 'wb') as f:
                        f.write(body)                    
            print(cmd, param, headers)
            # send response
            if cmd:
                resp_type, response = respond(cmd, param)
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

    sleep_ms(3000)
    WLAN_disconnect()
#end run_tcp_server


if __name__ == "__main__":
    run_tcp_server(2323)