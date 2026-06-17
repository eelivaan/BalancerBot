import asyncio
import threading
from bleak import BleakScanner, BleakClient
from queue import Queue
import json

DEVICE_NAME = "PicoBLE"

# Nordic UART Service UUIDs
UART_TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Pico sends here (notify)
UART_RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # We write here


class BLEThread(threading.Thread):
    def __init__(self, allow_string_messages=False):
        super().__init__(daemon=True)
        self.receiving_log = False
        self.msg_buffer = bytearray()
        self.msgQueue = Queue()
        self.sendQueue = Queue()
        self.connected_flag = threading.Event()
        self.stop_flag = threading.Event()
        self.ok_flag = threading.Event()
        self.log = []  # Store log data received from Pico
        self.display_log_flag = threading.Event()
        self.allow_str_messages = allow_string_messages

    def is_connected(self):
        return self.connected_flag.is_set()

    def send(self, msg):
        self.sendQueue.put(msg)

    def read(self):
        if not self.msgQueue.empty():
            return self.msgQueue.get_nowait()
        else:
            return None
        
    def check_ack(self):
        if self.ok_flag.is_set():
            self.ok_flag.clear()
            return True
        else:
            return False
        
    def read_log(self):
        if self.display_log_flag.is_set():
            self.display_log_flag.clear()
            return self.log
        else:
            return None

    def stop(self):
        self.stop_flag.set()

    # called when data is received from Pico
    def on_notify(self, sender, data: bytearray):
        self.msg_buffer.extend(data)
        if b'\0' in self.msg_buffer:
            (msg, self.msg_buffer) = self.msg_buffer.split(b'\0', 1)  # Split at null terminator
            message = msg.decode("utf-8", errors="replace").strip()
            if message == "ok":
                self.ok_flag.set()
            elif message == "log_output":
                self.log.clear()
                self.receiving_log = True
                self.msgQueue.put("wait...")
            elif message == "log_end":
                self.receiving_log = False
                self.display_log_flag.set()
            elif self.receiving_log:
                self.log.append(message)
            elif self.allow_str_messages:
                self.msgQueue.put(message)
            else:
                try:
                    js = json.loads(message)  # Validate JSON
                    self.msgQueue.put(js)
                except json.JSONDecodeError:
                    print(f"Pico: {message}")
    #end on_notify

    async def main(self):
        while not self.stop_flag.is_set():
            print(f"Scanning for '{DEVICE_NAME}'...")
            try:
                device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=5.0)
            except Exception as e:
                print(f"Error during BLE scan: {e}")
                await asyncio.sleep(5)
                continue

            if device is None:
                print("Device not found. Make sure main.py is running on the Pico.")
            else:
                print(f"Found: {device.name} [{device.address}]")

                async with BleakClient(device) as client:
                    print("Connected. Subscribing to notifications...")
                    await client.start_notify(UART_TX_UUID, self.on_notify)
                    self.connected_flag.set()
                    print("Ready.\n")

                    while not self.stop_flag.is_set() and client.is_connected:
                        if not self.sendQueue.empty():
                            msg = self.sendQueue.get_nowait() + '\0'
                            # 20 char limit per BLE packet, so split if needed
                            for i in range(0, len(msg), 20):
                                chunk = msg[i:i+20]
                                await client.write_gatt_char(UART_RX_UUID, chunk.encode("utf-8"))
                        await asyncio.sleep(0.05)

                    if client.is_connected:
                        await client.stop_notify(UART_TX_UUID)
                        print("Disconnected.")
                    self.connected_flag.clear()
    #end async main

    def run(self):
        asyncio.run(self.main())
#end BLEThread
