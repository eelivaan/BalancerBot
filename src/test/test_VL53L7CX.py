from machine import I2C, Pin
from VL53L7CX import VL53L7CX # type: ignore
import time

led = Pin("LED", Pin.OUT)
led.on()

print("led on")

i2c0 = I2C(1, scl=Pin("GP7"), sda=Pin("GP6"), freq=400000)
print(i2c0)

time.sleep_ms(100)

sensor = VL53L7CX(i2c0, 8)

sensor.test_print("hello")

print("I2C Scan result: [", end='')
for addr in i2c0.scan():
    print(hex(addr), end='')
print("]")

print(sensor)

sensor.configure("4x4", 2)

sensor.start_ranging()

print(sensor)

for i in range(10):
    if sensor.is_data_ready():
        print(sensor.get_ranging_data())
    time.sleep_ms(300)

sensor.stop_ranging()

sensor.test_print("Ranging stopped")

led.off()