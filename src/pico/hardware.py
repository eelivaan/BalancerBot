from machine import Pin, ADC, PWM
import json

class BalancerBot:

    def __init__(self):
        self.led_builtin = Pin("LED", Pin.OUT)
        self.led_builtin.on()

        self.bat_adc = ADC(Pin("GP26"))

        self.config = {}
        self.load_config()


    def load_config(self):
        with open("config.json", "r") as f:
            self.config = json.load(f)
            pid.Kp = self.config['Kp']
            pid.Ki = self.config['Ki']
            pid.Kd = self.config['Kd']
            pid.target_value = self.config['target']


    def read_battery_percentage(self):
        raw = self.bat_adc.read_u16()
        voltage = raw / 65535.0 * 3.3 * 2
        return round((voltage - 3.40) / (4.20 - 3.40) * 100)
    