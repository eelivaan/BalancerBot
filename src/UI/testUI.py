import tkinter as tk
from tkinter import ttk
from ble_client import BLEThread


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
        if ble_thread.is_connected():
            while data := ble_thread.read():
                self.textmap[data[0]] = data[1:]
            text = ""
            for key, value in self.textmap.items():
                text += value + '\n'
            self.textarea.config(text=text)
            if ble_thread.check_ack():
                self.ok_label.grid()  # Show "ok" label
                self.after(2000, lambda: self.ok_label.grid_remove())
        else:
            self.textarea.config(text="N/A")

        self.after(50, self.tick)


    def destroy(self):
        super().destroy()
        ble_thread.stop()


    def send_stop_signal(self):
        ble_thread.send('stop')
#end GUIApp



if __name__ == "__main__":
    ble_thread = BLEThread(allow_string_messages=True)
    root = GUIApp()
    ble_thread.start()
    
    root.mainloop()

    if ble_thread.is_alive():
        ble_thread.join(1000)
