import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
import json
from ble_client import BLEThread


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
        if ble_thread.is_connected():
            if data := ble_thread.read():
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
                    text += f"Battery: {data['b']:.2f} V\n"
                    text += f"Distance: {data['d']:.1f} cm"
                    self.accel_label.config(text=text)
            if ble_thread.check_ack():
                self.ok_label.grid()  # Show "ok" label
                self.after(2000, lambda: self.ok_label.grid_remove())
            if log := ble_thread.read_log():
                self.show_log(log)
        else:
            self.accel_label.config(text="N/A")

        self.after(50, self.tick)


    def destroy(self):
        super().destroy()
        ble_thread.stop()
        self.update_config()
 

    def update_config(self):
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
                json.dump(config, f, indent=2) # type: ignore
                print("config.json updated")
    

    def send_pid(self):
        try:
            msg = json.dumps({"type": "pid0", 
                              "Kp": self.Kp0.get(), "Ki": self.Ki0.get(), "Kd": self.Kd0.get(), 
                              "target": self.target0.get(), "max": self.max0.get(), "en": self.enable_motors.get()})
            ble_thread.send(msg)
            for c in range(1,3):
                msg = json.dumps({"type": f"pid{c}", 
                                  "Kp": getattr(self, f'Kp{c}').get(), 
                                  "Ki": getattr(self, f'Ki{c}').get(), 
                                  "Kd": getattr(self, f'Kd{c}').get(), 
                                  "target": getattr(self, f'target{c}').get(), 
                                  "max": getattr(self, f'max{c}').get()})
                ble_thread.send(msg)
        except ValueError:
            pass  # Ignore invalid input


    def download_config(self):
        self.update_config()
        with open("config.json", "r") as f:
            content = f.read()
            msg = json.dumps({"type": "config", "content": content})
            ble_thread.send(msg)


    def send_typed(self, type: str):
        msg = json.dumps({"type": type})
        ble_thread.send(msg)


    def show_log(self, log: list):
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


ble_thread = BLEThread()
app = GUIApp()

ble_thread.start()    

app.mainloop()

if ble_thread.is_alive():
    ble_thread.join(1000)
