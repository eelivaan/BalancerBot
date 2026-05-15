import asyncio
import tkinter as tk
import threading
from bleak import BleakScanner, BleakClient
from queue import Queue
import json
import time

DEVICE_NAME = "PicoBLE"

# Nordic UART Service UUIDs
UART_TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Pico sends here (notify)
UART_RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # We write here

msgQueue = Queue()
sendQueue = Queue()
stop_flag = threading.Event()

def on_notify(sender, data: bytearray):
    message = data.decode("utf-8", errors="replace").strip()
    try:
        js = json.loads(message)  # Validate JSON
        msgQueue.put(js)
    except json.JSONDecodeError:
        print(f"Pico: {message}")


async def main():
    print(f"Scanning for '{DEVICE_NAME}'...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if device is None:
        print("Device not found. Make sure bt.py is running on the Pico.")
        return

    print(f"Found: {device.name} [{device.address}]")

    async with BleakClient(device) as client:
        print("Connected. Subscribing to notifications...")
        await client.start_notify(UART_TX_UUID, on_notify)
        print("Ready. Type messages to send (empty line to quit):\n")

        while not stop_flag.is_set():
            #line = await asyncio.get_event_loop().run_in_executor(None, input, "> ")
            #if line == "":
            #    break
            #await client.write_gatt_char(UART_RX_UUID, (line + "\n").encode("utf-8"))
            if not sendQueue.empty():
                msg = sendQueue.get_nowait() + "\n"
                # 20 char limit per BLE packet, so split if needed
                for i in range(0, len(msg), 20):
                    chunk = msg[i:i+20]
                    await client.write_gatt_char(UART_RX_UUID, chunk.encode("utf-8"))
            await asyncio.sleep(0.2)

        await client.stop_notify(UART_TX_UUID)
        print("Disconnected.")


class GUIApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pico BLE Client")
        self.geometry("700x400")

        self.accel_label = tk.Label(self, text="N/A", font=("Consolas", 11), justify="left", anchor="w")
        self.accel_label.grid(pady=20, padx=10, row=0, column=0, columnspan=3)

        for i, t in enumerate(["Kp", "Ki", "Kd"]):
            tk.Label(self, text=f"{t}:", font=("Consolas", 11)).grid(pady=10, padx=15, row=1, column=i*2)
            setattr(self, f"{t}Edit", tk.Spinbox(self, from_=0.0, to=10.0, increment=0.1, width=5))
            getattr(self, f"{t}Edit").grid(pady=10, padx=5, row=1, column=i*2+1)
            getattr(self, f"{t}Edit").configure(command=self.send_pid)  # Call send_pid on value change

        self.tick()

    def tick(self):
        if not msgQueue.empty():
            data = msgQueue.get_nowait()
            text = f"Accel: {data['a']['x']:.3f}  {data['a']['y']:.3f}  {data['a']['z']:.3f}\n"
            text += f"Gyro: {data['g']['x']:.3f}  {data['g']['y']:.3f}  {data['g']['z']:.3f}\n"
            text += f"Temp: {data['t']:.2f}°C"
            self.accel_label.config(text=text)
        self.after(100, self.tick)

    def destroy(self):
        super().destroy()
        stop_flag.set()

    def send_pid(self):
        try:
            Kp = float(self.KpEdit.get())
            Ki = float(self.KiEdit.get())
            Kd = float(self.KdEdit.get())
            msg = json.dumps({"Kp": Kp, "Ki": Ki, "Kd": Kd})
            sendQueue.put(msg)
        except ValueError:
            pass  # Ignore invalid input
        
        


if __name__ == "__main__":
    root = GUIApp()

    ble_thread = threading.Thread(target=lambda: asyncio.run(main()), daemon=True)
    ble_thread.start()
    
    root.mainloop()

    if ble_thread.is_alive():
        ble_thread.join(1000)