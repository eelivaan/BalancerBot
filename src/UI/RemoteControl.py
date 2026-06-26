import json

import tkinter as tk
from tkinter import ttk
from ble_client import BLEThread


class RemoteControlUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Remote Control")
        self.geometry("400x300")
        self.configure(bg="#1e1e1e")
        self.focus_set()
        self.pressed_keys = set()
        self.bind("<KeyPress>", self.key_down)
        self.bind("<KeyRelease>", self.key_up)
        self.bind("<KeyPress-Escape>", lambda event: self.destroy())  # Press Escape to quit

        font = ("Consolas", 11)
        self.text_label = ttk.Label(self, text="No connection", font=font, justify="left", anchor="w", width=70, foreground="#e0e0e0", background="#1e1e1e")
        self.text_label.pack(padx=10, pady=10)

        self.motors_btn = ttk.Button(self, text="Enable motors", command=self.lift)
        self.motors_btn.pack(side="left", padx=10, pady=10, ipadx=5)

        self.stop_btn = ttk.Button(self, text="Stop program", command=self.quit)
        self.stop_btn.pack(side="left", padx=10, pady=10, ipadx=5)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background="#1e1e1e", foreground="#e0e0e0")
        style.configure('TButton', background="#2d2d2d", foreground="#e0e0e0")
        style.map('TButton', background=[('active', '#3d3d3d')])

        self.ok_label = ttk.Label(self, text="ok", font=("Consolas", 14), background="#11662d", justify="center", anchor="center")
        self.ok_label.pack_forget()  # Hide initially

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
                self.turn(30)
            elif 'd' in self.pressed_keys:
                self.turn(-30)

    def key_up(self, event):
        if event.keysym in self.pressed_keys:
            self.pressed_keys.remove(event.keysym)
        if not self.pressed_keys:
            self.stop()

    def forward(self):
        ble_thread.send(json.dumps({'type': 'rc', 'sp': 0.5, 'hd': self.target_heading}))

    def backward(self):
        ble_thread.send(json.dumps({'type': 'rc', 'sp': -0.5, 'hd': self.target_heading}))

    def lift(self):
        ble_thread.send(json.dumps({'type': 'motors_en', 'en': True}))

    def stop(self):
        ble_thread.send(json.dumps({'type': 'rc', 'sp': 0.0, 'hd': self.target_heading}))

    def turn(self, a):
        self.target_heading = (self.target_heading + a) % 360
        ble_thread.send(json.dumps({'type': 'rc', 'sp': 0.0, 'hd': self.target_heading}))

    def quit(self):
        ble_thread.send(json.dumps({'type': 'quit'}))
        

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
                self.ok_label.pack(side="left", padx=10, pady=10, ipadx=5)
                self.after(1000, lambda: self.ok_label.pack_forget())
        else:
            self.text_label.config(text="No connection")

        self.after(100, self.tick)
#end RemoteControlUI


if __name__ == "__main__":
    ble_thread = BLEThread()
    app = RemoteControlUI()
    ble_thread.start()
    app.mainloop()
    if ble_thread.is_alive():
        ble_thread.join(1000)

