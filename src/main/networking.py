"""
    Interface for running a TCP file transfer server in local network
"""
import network, socket, os, machine, select, time
from machine import Pin, ADC, Timer
from wlancredentials import SSID, PASSWORD

led = Pin("LED", Pin.OUT)
blink_timer = Timer(-1)
wlan = None
html = ''

def reload_status_html():
    global html
    with open('status.html', 'r') as f:
        html = f.read()

def read_battery_voltage():
    bat_adc = ADC(Pin("GP26"))
    raw = bat_adc.read_u16()
    return raw / 65535.0 * 3.3 * 2

def status_response():
    if html == '':
        reload_status_html()
    # list files in pico
    filetree = '<br>'.join([f"|- <a href='/{f}'>{f}</a> ({os.stat(f)[6] / 1000:.1f} kB)" for f in os.listdir()])
    dtm = time.localtime(time.time())
    return 'text/html', html % (read_battery_voltage(), 
                                f'{dtm[3]:02}:{dtm[4]:02}:{dtm[5]:02}', 
                                filetree)


def WLAN_connect():
    """ Connect to local wireless network for e.g. mpremote access """
    global wlan

    led.on()

    # connect to newwork
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print('WLAN active')
    wlan.config(pm = 0xa11140) # Power saving mode off

    print(f'WLAN trying to connect "{SSID}"')
    wlan.connect(SSID, PASSWORD)

    # Wait for connection for 10 seconds or fail
    print('WLAN waiting for connection...', end='')
    for i in range(10):
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        print('.', end='')
        led.off()
        time.sleep_ms(100)
        led.on()
        time.sleep_ms(900)
    print()

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
    global wlan

    if wlan:
        if wlan.status() == 3:
            wlan.disconnect()
            print('WLAN disconnected')

        wlan.active(False)
        print('WLAN inactive')
    led.off()


def WLAN_startAP():
    """ Start WLAn in access point mode """
    global wlan

    led.on()

    # connect to newwork
    wlan = network.WLAN(network.AP_IF)
    # Power saving mode off, WiFi name, WiFi password, security protocol
    wlan.active(True)
    wlan.config(pm = 0xa11140, ssid='Pico AP2', key='pico_2026', security=3, hidden=False)
    print('AP activating...', end='')
    while not wlan.active():
        print('.', end='')
    print('\nWLAN AP available as "Pico AP2" (pico_2026)...')

    status = wlan.ifconfig()
    print('ip = ' + status[0])

    return True


def run_tcp_server(port=2323, stopcondition=lambda: False):
    # connect to existing network or start AP
    if not WLAN_connect():
        led.off()
        wlan.active(False) # type: ignore
        #print()
        #time.sleep_ms(1000)
        #if not WLAN_startAP():
        return

    # start server
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    server_socket = socket.socket()
    server_socket.settimeout(None)  # blocking mode
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(addr)
    server_socket.listen(1)

    print(f"Listening on port {port}...", end='')
    server_running = True
    boot_requested = False
    
    while server_running and not stopcondition():
        print('.', end='')

        try:
            # poll socket with 1 second timeout
            rlist, wlist, errlist = select.select([server_socket], [], [], 1) # type: ignore
            if server_socket not in rlist:
                continue
        except KeyboardInterrupt as e:
            break

        print()
        try:
            (client, client_addr) = server_socket.accept()
            print("Client connected:", client_addr)

            blink_timer.init(period=70, callback=lambda t: led.toggle()) # start blinking

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
            #print(cmd, path, headers)

            # read request body
            content_length = int(headers['content-length'])
            resp_type, response = 'text/plain', ''
            not_found = False

            if content_length > 0:
                if cmd == 'POST':
                    # save content to file
                    if 'form-data' in headers['content-type']:
                        boundary = cl_file.readline().strip()
                        content_disposition = cl_file.readline().strip()
                        content_type = cl_file.readline().strip()
                        with open('.'+path, 'wb') as f:
                            while line := cl_file.readline():
                                if boundary in line:
                                    break
                                f.write(line)
                        if 'status.html' in path:
                            reload_status_html()
                        response = 'upload-ok'
                    # read command
                    elif 'text/plain' in headers['content-type']:
                        cmd = cl_file.read(content_length).decode().strip()
                        print(cmd)
                else:
                    while cl_file.readline(): pass

            filesize = None
            if cmd == 'GET':
                if path != '/':
                    try:
                        # test file existence
                        filesize = os.stat('.'+path)[6]
                        print('File size', filesize, 'bytes')
                    except OSError as e:
                        not_found = True
                else:
                    resp_type, response = status_response()
            elif cmd == 'QUIT':
                server_running = False
                response = 'quit-ok'
            elif cmd == 'BOOT':
                server_running = False
                boot_requested = True
                response = 'boot-ok'
            elif cmd == 'PING':
                response = 'ping-ok'

            # send response
            if not_found:
                client.send('HTTP/1.0 404 Not Found\r\n\r\n')
            elif response or filesize:
                client.send(f'HTTP/1.0 200 OK\r\n'
                            f'Content-type: {resp_type}\r\n'
                            f'Content-length: {filesize if filesize else len(response)}\r\n'
                            f'Cache-Control: no-cache\r\n'
                            '\r\n')
                if filesize:
                    # send requested file in chunks of 1024 bytes
                    with open('.'+path, 'r') as f:
                        while chunk := f.read(1024):
                            client.sendall(chunk)
                else:
                    client.sendall(response)
            else:
                client.send('HTTP/1.0 400 Bad Request\r\n\r\n')

            client.close()

        except OSError as e:
            client.close()
            print("Error:", e)

        time.sleep_ms(200)
        blink_timer.deinit() # stop blinking
        led.on()
    #end while

    print()
    # stop TCP server
    server_socket.close()
    print('Server closed')
    time.sleep_ms(1500)
    WLAN_disconnect()

    if boot_requested:
        print('Soft reset...')
        machine.soft_reset()
#end run_tcp_server


if __name__ == "__main__":
    run_tcp_server(2323)