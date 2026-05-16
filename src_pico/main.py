from machine import Pin, PWM, Timer, I2C
from utime import sleep_ms
from mpu6050 import mpu6050
from BLESerial import BLESerial
from control import PIDController
import json

led_builtin = Pin("LED", Pin.OUT)
led_external = Pin("GP18", Pin.OUT)
led_external_PWM = PWM(led_external, freq=1000)

blink_timer = Timer(-1)
blink_timer.init(period=400, callback=lambda t: led_builtin.toggle())

i2c = I2C(0, scl=Pin("GP21"), sda=Pin("GP20"), freq=100000)
print("I2C Scan result: ", end='')
for addr in i2c.scan():
    print(hex(addr))
mpu = mpu6050(0x68, i2c)

pid = PIDController()

loop_interval = 100  # ms

def ble_msg_callback(msg):
    global loop_interval
    print("Received BLE message: ", msg)
    try:
        params = json.loads(msg)
        pid.Kp = params["Kp"]
        pid.Ki = params["Ki"]
        pid.Kd = params["Kd"]
        pid.target_value = params["tgt"]
        loop_interval = params["intv"]
    except (json.JSONDecodeError, KeyError) as e:
        pass

ble = BLESerial(ble_msg_callback)

while True:
    try:
        accel = mpu.get_accel_data()
        signal = 0.0 if abs(accel['z']) > 7.0 else pid.calcPID(accel['z'])
        led_external_PWM.duty_u16(min(65535, round(abs(signal) * 65535.0)))

        data = {'a': accel, 'g': mpu.get_gyro_data(), 't': mpu.get_temp()}
        ble.send(json.dumps(data))

        sleep_ms(loop_interval)

    except KeyboardInterrupt:
        break

blink_timer.deinit()
led_builtin.off()
led_external_PWM.duty_u16(0)
#led_external_PWM.deinit()
ble.deactivate()
print("Finished.")