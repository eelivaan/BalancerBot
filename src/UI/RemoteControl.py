import json

import tkinter as tk
from tkinter import ttk
from ble_client import BLEThread


class RemoteControlUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Remote Control")
        self.geometry("400x300")
        self.focus_set()
        self.pressed_keys = set()
        self.bind("<KeyPress>", self.key_down)
        self.bind("<KeyRelease>", self.key_up)

        font = ("Consolas", 11)
        self.text_label = ttk.Label(self, text="N/A", font=font, justify="left", anchor="w", width=70)
        self.text_label.pack(padx=10, pady=10)
        self.ok_label = ttk.Label(self, text="", font=("Consolas", 14), foreground="#0b0c0b", background="#a3f9a3")
        self.ok_label.pack()

        self.target_speed = 0.0
        self.target_heading = 0.0

        self.tick()

    def destroy(self):
        super().destroy()
        ble_thread.stop()

    def key_down(self, event):
        if event.keysym not in self.pressed_keys:
            self.pressed_keys.add(event.keysym)
            if 'w' in self.pressed_keys:
                self.forward()
            elif 's' in self.pressed_keys:
                self.backward()
            elif 'a' in self.pressed_keys:
                self.turn(45)
            elif 'd' in self.pressed_keys:
                self.turn(-45)

    def key_up(self, event):
        if event.keysym in self.pressed_keys:
            self.pressed_keys.remove(event.keysym)
        if not self.pressed_keys:
            self.stop()

    def forward(self):
        ble_thread.send(json.dumps({'type': 'rc', 'sp': 0.5, 'hd': self.target_heading}))

    def backward(self):
        ble_thread.send(json.dumps({'type': 'rc', 'sp': -0.5, 'hd': self.target_heading}))

    def stop(self):
        ble_thread.send(json.dumps({'type': 'rc', 'sp': 0.0, 'hd': self.target_heading}))

    def turn(self, a):
        self.target_heading = (self.target_heading + a) % 360
        ble_thread.send(json.dumps({'type': 'rc', 'sp': 0.0, 'hd': self.target_heading}))
        

    def tick(self):
        if ble_thread.is_connected():
            #if 'a' in self.pressed_keys:
            #    self.turn(5.0)
            #elif 'd' in self.pressed_keys:
            #    self.turn(-5.0)

            while data := ble_thread.read():
                if isinstance(data, str):
                    self.text_label.config(text=data)
                else:
                    text = f"Heading: {data['h']:.1f}°\n"
                    text += f"Temperature: {data['t']:.2f}°C\n"
                    text += f"Distance: {data['d']:.1f} cm\n"
                    text += f"Motor Speed: {data['mt']:.3f}\n"
                    text += f"Battery: {data['b']:.2f} V\n"
                    self.text_label.config(text=text)
            if ble_thread.check_ack():
                self.ok_label.configure(text="ok")
                self.after(1500, lambda: self.ok_label.configure(text=""))
        else:
            self.text_label.config(text="N/A")

        self.after(100, self.tick)
#end RemoteControlUI


if __name__ == "__main__":
    ble_thread = BLEThread()
    app = RemoteControlUI()
    ble_thread.start()
    app.mainloop()
    if ble_thread.is_alive():
        ble_thread.join(1000)

