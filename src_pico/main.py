from machine import Pin, PWM, Timer, I2C
from utime import sleep_ms
from mpu6050 import mpu6050
from BLESerial import BLESerial
import json

led_builtin = Pin("LED", Pin.OUT)
led_external = Pin("GP18", Pin.OUT)
led_external_PWM = PWM(led_external, freq=1000)

#led_external.high()
duty = 0

tim1 = Timer(-1)
tim1.init(period=600, callback=lambda t: led_builtin.toggle())

def ble_msg_callback(msg):
    print("Received BLE message: ", msg)

ble = BLESerial(ble_msg_callback)

i2c = I2C(0, scl=Pin("GP21"), sda=Pin("GP20"), freq=100000)
print("I2C Scan result: ", end='')
for addr in i2c.scan():
    print(hex(addr))
mpu = mpu6050(0x68, i2c)

while True:
    try:
        led_external_PWM.duty_u16(duty * duty)
        duty = (duty + 16) % 255

        data = {'a': mpu.get_accel_data(), 'g': mpu.get_gyro_data(), 't': mpu.get_temp()}
        ble.send(json.dumps(data))

        sleep_ms(500)

    except KeyboardInterrupt:
        break

led_builtin.off()

led_external_PWM.duty_u16(0)
#led_external_PWM.deinit()

ble.deactivate()

print("Finished.")