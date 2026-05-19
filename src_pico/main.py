from machine import Pin, PWM, Timer, I2C
from utime import sleep_us, ticks_ms, ticks_us, ticks_diff
from mpu6050 import mpu6050
from BLESerial import BLESerial
from control import PIDController
import json

led_builtin = Pin("LED", Pin.OUT)
led_external = Pin("GP22", Pin.OUT)
led_external_PWM = PWM(led_external, freq=1000)

blink_timer = Timer(-1)
blink_timer.init(period=400, callback=lambda t: led_builtin.toggle())

i2c = I2C(0, scl=Pin("GP21"), sda=Pin("GP20"), freq=400000)
print("I2C Scan result: ", end='')
for addr in i2c.scan():
    print(hex(addr))
mpu = mpu6050(0x68, i2c)

pid = PIDController()

config = {}
def load_config():
    global config
    with open("config.json", "r") as f:
        config = json.load(f)
        pid.Kp = config['Kp']
        pid.Ki = config['Ki']
        pid.Kd = config['Kd']
        pid.target_value = config['target']
load_config()

def ble_msg_callback(msg):
    print("Received BLE message")
    try:
        params = json.loads(msg)
        # update PID params
        if params.get('type') == 'pid':
            pid.Kp = params['Kp']
            pid.Ki = params['Ki']
            pid.Kd = params['Kd']
            pid.target_value = params['tgt']
        # download config file
        elif params.get('type') == 'config':
            with open("config.json", "w") as f:
                f.write(params['content'])
            load_config()  # Reload config to apply changes
    except (json.JSONDecodeError, KeyError) as e:
        print("Unhandled BLE message: ", msg)

ble = BLESerial(ble_msg_callback)

history_x = []
filtered_x = 0.0

prev_status_time = ticks_ms()
dt = 0

while True:
    try:
        t1 = ticks_us()

        # measure and filter acceleration
        accel = mpu.get_accel_data()
        x = accel[config['channel']] # type: ignore

        if config['filter'] > 0:
            history_x.append(x)
            #filtered_x += x / config['filter']
            if len(history_x) > config['filter']:
                history_x.pop(0)
                #filtered_x -= history_x.pop(0) / config['filter']
            filtered_x = sum(history_x) / len(history_x)

            signal = 0.0 if abs(filtered_x) > config['limit'] else pid.calcPID(filtered_x)
        else:
            signal = 0.0 if abs(x) > config['limit'] else pid.calcPID(x)

        # motor control
        led_external_PWM.duty_u16(min(65535, round(abs(signal) * 65535.0)))

        # send status info to laptop
        if ble.is_connected() and ticks_diff(ticks_ms(), prev_status_time) > config['status_send_period']:
            prev_status_time = ticks_ms()
            data = {'a': accel, 'g': mpu.get_gyro_data(), 't': mpu.get_temp(), 's': filtered_x, 'dt': dt}
            ble.send(json.dumps(data))

        t2 = ticks_us()
        dt = ticks_diff(t2, t1)

        sleep_us(max(10, config['loop_interval']*1000 - dt))

    except KeyboardInterrupt:
        break

    except Exception as e:
        print("Error in main loop:", e)
        break
#end while

blink_timer.deinit()
led_builtin.off()
led_external_PWM.duty_u16(0)
#led_external_PWM.deinit()
ble.deactivate()
print("Finished.")