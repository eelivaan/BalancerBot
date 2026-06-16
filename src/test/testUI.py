import asyncio
import tkinter as tk
from tkinter import ttk
import threading
from bleak import BleakScanner, BleakClient
from queue import Queue
import json

DEVICE_NAME = "PicoBLE"

# Nordic UART Service UUIDs
UART_TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Pico sends here (notify)
UART_RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # We write here

msgQueue = Queue()
sendQueue = Queue()
connected_flag = threading.Event()
stop_flag = threading.Event()
ok_flag = threading.Event()


# called when data is received from Pico
def on_notify(sender, data: bytearray):
    message = data.decode("utf-8", errors="replace").strip()
    if message == "ok":
        ok_flag.set()
    else:
        msgQueue.put(message)


async def main():
    while not stop_flag.is_set():
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
                await client.start_notify(UART_TX_UUID, on_notify)
                connected_flag.set()
                print("Ready.\n")

                while not stop_flag.is_set() and client.is_connected:
                    if not sendQueue.empty():
                        msg = sendQueue.get_nowait() + '\0'
                        # 20 char limit per BLE packet, so split if needed
                        for i in range(0, len(msg), 20):
                            chunk = msg[i:i+20]
                            await client.write_gatt_char(UART_RX_UUID, chunk.encode("utf-8"))
                    await asyncio.sleep(0.05)

                if client.is_connected:
                    await client.stop_notify(UART_TX_UUID)
                    print("Disconnected.")
                connected_flag.clear()
#end async main


class GUIApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Testing UI")
        self.geometry("600x450")

        font = ("Consolas", 11)
        style = ttk.Style()
        style.theme_use('clam')

        self.textarea = ttk.Label(self, text="N/A", font=font, justify="left", anchor="w", width=70)
        self.textarea.grid(pady=20, padx=10, row=0, column=0, columnspan=10)
        self.textmap = {}

        self.stop_btn = ttk.Button(self, text="Stop program", command=self.send_stop_signal)
        self.stop_btn.grid(pady=10, padx=5, row=1, column=0)

        self.ok_label = ttk.Label(self, text="ok", font=("Consolas", 14), foreground="#0b0c0b", background="#a3f9a3")
        self.ok_label.grid(pady=10, padx=5, row=1, column=1)
        self.ok_label.grid_remove()  # Hide initially

        self.tick()


    def tick(self):
        if connected_flag.is_set():
            if not msgQueue.empty():
                data = msgQueue.get_nowait()
                self.textmap[data[0]] = data[1:]
                text = ""
                for key, value in self.textmap.items():
                    text += value + '\n'
                self.textarea.config(text=text)
            if ok_flag.is_set():
                self.ok_label.grid()  # Show "ok" label
                ok_flag.clear()
                self.after(2000, lambda: self.ok_label.grid_remove())
        else:
            self.textarea.config(text="N/A")

        self.after(50, self.tick)


    def destroy(self):
        super().destroy()
        stop_flag.set()


    def send_stop_signal(self):
        sendQueue.put('stop')
#end GUIApp



if __name__ == "__main__":
    root = GUIApp()

    ble_thread = threading.Thread(target=lambda: asyncio.run(main()), daemon=True)
    ble_thread.start()
    
    root.mainloop()

    if ble_thread.is_alive():
        ble_thread.join(1000)
