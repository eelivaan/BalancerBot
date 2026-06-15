import asyncio
import tkinter as tk
from tkinter import ttk
import threading
from bleak import BleakScanner, BleakClient
from queue import Queue
import json
import numpy as np
import matplotlib.pyplot as plt

DEVICE_NAME = "PicoBLE"

# Nordic UART Service UUIDs
UART_TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Pico sends here (notify)
UART_RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # We write here

msgQueue = Queue()
sendQueue = Queue()
connected_flag = threading.Event()
stop_flag = threading.Event()
ok_flag = threading.Event()

log = []  # Store log data received from Pico
display_log_flag = threading.Event()

class BLEThread(threading.Thread):
    receiving_log = False
    msg_buffer = bytearray()

    # called when data is received from Pico
    def on_notify(self, sender, data: bytearray):
        self.msg_buffer.extend(data)
        if b'\0' in self.msg_buffer:
            (msg, self.msg_buffer) = self.msg_buffer.split(b'\0', 1)  # Split at null terminator
            message = msg.decode("utf-8", errors="replace").strip()
            if message == "ok":
                ok_flag.set()
            elif message == "log_output":
                log.clear()
                self.receiving_log = True
                msgQueue.put("wait...")
            elif message == "log_end":
                self.receiving_log = False
                display_log_flag.set()
            elif self.receiving_log:
                log.append(message)
            else:
                try:
                    js = json.loads(message)  # Validate JSON
                    msgQueue.put(js)
                except json.JSONDecodeError:
                    print(f"Pico: {message}")
    #end on_notify

    async def main(self):
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
                    await client.start_notify(UART_TX_UUID, self.on_notify)
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

    def run(self):
        asyncio.run(self.main())
#end BLEThread


class GUIApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Control Panel")
        self.geometry("600x550")

        font = ("Consolas", 11)
        style = ttk.Style()
        style.theme_use('clam')

        self.accel_label = ttk.Label(self, text="N/A", font=font, justify="left", anchor="w", width=70)
        self.accel_label.grid(pady=20, padx=10, row=0, column=0, columnspan=10)

        self.enable_motors = tk.BooleanVar(value=False)
        self.motors_checkbox = ttk.Checkbutton(self, text="Enable Motors", variable=self.enable_motors)
        self.motors_checkbox.grid(pady=5, padx=5, row=1, column=0)
        self.motors_checkbox.configure(command=self.send_pid)  # Call send_pid when toggled

        # load initial PID values from config.json
        with open("config.json", "r") as f:
            config = json.load(f)

        for i, t in enumerate(["Kp", "Ki", "Kd", "target", "max"]):
            ttk.Label(self, text=f"{t}:", font=font).grid(pady=5, padx=5, row=2+i, column=0)
            for c in range(3):
                var = tk.DoubleVar(value=config[f'pid{c}'].get(t))
                setattr(self, f"{t}{c}", var)
                spinBox = ttk.Spinbox(self, from_=0.0, to=10.0, increment=0.001, textvariable=var, width=7)
                setattr(self, f"{t}{c}Edit", spinBox)
                spinBox.grid(pady=5, padx=5, row=2+i, column=1+c)
                spinBox.configure(command=self.send_pid)  # Call send_pid on value change
                spinBox.bind("<Return>", lambda event: self.send_pid())  # Call send_pid on enter key

        self.download_btn = ttk.Button(self, text="Download config.json", command=self.download_config)
        self.download_btn.grid(pady=10, padx=5, row=7, column=0)

        self.stop_btn = ttk.Button(self, text="Stop program", command=lambda: self.send_typed('quit'))
        self.stop_btn.grid(pady=10, padx=5, row=7, column=1)

        self.calibrate_btn = ttk.Button(self, text="Calibrate", command=lambda: self.send_typed('calibrate'))
        self.calibrate_btn.grid(pady=10, padx=5, row=7, column=2)

        self.log_btn = ttk.Button(self, text="Capture", command=lambda: self.send_typed('log'))
        self.log_btn.grid(pady=10, padx=5, row=7, column=3)

        self.ok_label = ttk.Label(self, text="ok", font=("Consolas", 14), foreground="#0b0c0b", background="#a3f9a3")
        self.ok_label.grid(pady=10, padx=5, row=8, column=0)
        self.ok_label.grid_remove()  # Hide initially

        self.tick()
        self.send_pid()  # Send initial PID values to Pico


    def tick(self):
        if connected_flag.is_set():
            if not msgQueue.empty():
                data = msgQueue.get_nowait()
                if isinstance(data, str):
                    self.accel_label.config(text=data)
                else:
                    text = f"Accel: {data['a']['x']:.3f}  {data['a']['y']:.3f}  {data['a']['z']:.3f}\n"
                    text += f"Gyro: {data['g']['x']:.3f}  {data['g']['y']:.3f}  {data['g']['z']:.3f}\n"
                    text += f"Magnetometer: {data['m']['x']:.0f}  {data['m']['y']:.0f}  {data['m']['z']:.0f}\n"
                    text += f"Temperature: {data['t']:.2f}°C\n"
                    text += f"Filtered Pitch: {data['s']:.3f}°\n"
                    text += f"Pitch Target: {data['st']:.3f}°\n"
                    text += f"Heading: {data['h']:.1f}°\n"
                    text += f"Motor Speed: {data['mt']:.3f}\n"
                    text += f"Loop dt: {data['dt'] / 1000.0:.3f} ms\n"
                    text += f"Battery: {data['b']:.2f} V"
                    self.accel_label.config(text=text)
            if ok_flag.is_set():
                self.ok_label.grid()  # Show "ok" label
                ok_flag.clear()
                self.after(2000, lambda: self.ok_label.grid_remove())
            if display_log_flag.is_set():
                self.show_log()
                display_log_flag.clear()
        else:
            self.accel_label.config(text="N/A")

        self.after(50, self.tick)


    def destroy(self):
        super().destroy()
        stop_flag.set()
        with open("config.json", "r") as f:
            config = json.load(f)
            for c in range(3):
                pid = config[f'pid{c}']
                pid['Kp'] = getattr(self, f'Kp{c}').get()
                pid['Ki'] = getattr(self, f'Ki{c}').get()
                pid['Kd'] = getattr(self, f'Kd{c}').get()
                pid['target'] = getattr(self, f'target{c}').get()
                pid['max'] = getattr(self, f'max{c}').get()
            with open("config.json", "w") as f:
                json.dump(config, f, separators=(',\n', ': ')) # type: ignore
                print("config.json updated")
    

    def send_pid(self):
        try:
            msg = json.dumps({"type": "pid0", 
                              "Kp": self.Kp0.get(), "Ki": self.Ki0.get(), "Kd": self.Kd0.get(), 
                              "target": self.target0.get(), "max": self.max0.get(), "en": self.enable_motors.get()})
            sendQueue.put(msg)
            for c in range(1,3):
                msg = json.dumps({"type": f"pid{c}", 
                                  "Kp": getattr(self, f'Kp{c}').get(), 
                                  "Ki": getattr(self, f'Ki{c}').get(), 
                                  "Kd": getattr(self, f'Kd{c}').get(), 
                                  "target": getattr(self, f'target{c}').get(), 
                                  "max": getattr(self, f'max{c}').get()})
                sendQueue.put(msg)
        except ValueError:
            pass  # Ignore invalid input


    def download_config(self):
        with open("config.json", "r") as f:
            content = f.read()
            msg = json.dumps({"type": "config", "content": content})
            sendQueue.put(msg)


    def send_typed(self, type: str):
        msg = json.dumps({"type": type})
        sendQueue.put(msg)


    def show_log(self):
        fields = log[0].split(',')
        series = dict()
        for f in fields:
            series[f] = np.zeros(len(log)-1)

        for i, line in enumerate(log[1:]):
            values = line.split(',')
            for j, f in enumerate(fields):
                if f == 'pitch':
                    series[f][i] = float(values[j]) - self.target0.get()
                else:
                    series[f][i] = float(values[j])

        if 'time' not in series:
            print("Log does not contain a 'time' field.")
            return

        x = series['time']
        plt.figure("Log Plot")
        plt.clf()
        for f in fields:
            if f == 'time':
                continue
            plt.plot(x, series[f], label=f)

        plt.xlabel('time (s)')
        plt.ylabel('value')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show(block=False)
        
#end GUIApp



if __name__ == "__main__":
    root = GUIApp()

    ble_thread = BLEThread(daemon=True)
    ble_thread.start()
    
    root.mainloop()

    if ble_thread.is_alive():
        ble_thread.join(1000)
