from machine import Pin, PWM, Timer, I2C, ADC
from utime import sleep_us, sleep, ticks_ms, ticks_us, ticks_diff
from icm20948 import QwiicIcm20948, acc_d23bw9_n34bw4
from BLESerial import BLESerial
from control import PIDController
import json, math

led_builtin = Pin("LED", Pin.OUT)
led_builtin.on()

# wait button press to start execution
print("Press button to start...")
start_btn = Pin("GP22", Pin.IN, Pin.PULL_UP)
while start_btn.value(): sleep(0.1)
last_btn_press = ticks_ms()

blink_timer = Timer(-1)
blink_timer.init(period=400, callback=lambda t: led_builtin.toggle())

i2c = I2C(0, scl=Pin("GP21"), sda=Pin("GP20"), freq=400000)
print("I2C Scan result: ", end='')
for addr in i2c.scan():
    print(hex(addr))
IMU = QwiicIcm20948(i2c)

bat_adc = ADC(Pin("GP26"))

def read_battery_percentage():
    raw = bat_adc.read_u16()
    voltage = raw / 65535.0 * 3.3 * 2
    return round((voltage - 3.40) / (4.20 - 3.40) * 100)

servo1_PWM = PWM(Pin("GP12"), freq=50)
servo2_PWM = PWM(Pin("GP13"), freq=50)
motors_enabled = False

pid = PIDController()

def reset_control():
    global motors_enabled
    motors_enabled = True
    pid.err_integral = 0.0

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

quit_flag = False

def ble_msg_callback(msg):
    global motors_enabled, quit_flag
    print("Received BLE message")
    try:
        params = json.loads(msg)
        # update PID params
        if params.get('type') == 'pid':
            pid.Kp = params['Kp']
            pid.Ki = params['Ki']
            pid.Kd = params['Kd']
            pid.target_value = params['tgt']
            pid.err_integral = 0.0
            motors_enabled = params['en']
        # download config file
        elif params.get('type') == 'config':
            with open("config.json", "w") as f:
                f.write(params['content'])
            load_config()  # Reload config to apply changes
        elif params.get('type') == 'quit':
            quit_flag = True
    except (json.JSONDecodeError, KeyError) as e:
        print("Unhandled BLE message: ", msg)

ble = BLESerial(ble_msg_callback)

value_history = []
filtered_angle = 0.0
heading = 0.0

prev_status_time = ticks_ms()
dt = 0

signal_change_counter = 0

data_file = None # open("data.csv", "w")
if data_file:
    data_file.write("time, ax,ay,az, gx,gy,gz\n")
    print("Opened data.csv")

b = IMU.begin()
if not b:
    print("IMU initialization unsuccessful")
    quit_flag = True

IMU.enableDlpfAccel(True)
IMU.setDLPFcfgAccel(acc_d23bw9_n34bw4)

while not quit_flag:
    try:
        t1 = ticks_us()

        if IMU.dataReady():
            IMU.getAgmt() # read all axis and temp from sensor, note this also updates all instance variables
        
        # measure and filter acceleration
        accel = IMU.get_accel()
        a = accel[config['horiz_axis']]
        b = accel[config['vert_axis']]
        pitch_angle = math.degrees(math.atan(a / b)) if b != 0 else 0

        if config['filter'] > 0:
            value_history.append(pitch_angle)
            #filtered_x += x / config['filter']
            if len(value_history) > config['filter']:
                value_history.pop(0)
                #filtered_x -= history_x.pop(0) / config['filter']
            filtered_angle = sum(value_history) / len(value_history)
        else:
            filtered_angle = pitch_angle

        if abs(filtered_angle) > config['limit']:
            signal = 0.0
        else:
            signal = pid.calcPID(filtered_angle, config['loop_interval'] / 1000.0)
            signal = max(signal, -1.0) if signal < 0 else min(signal, 1.0)

        # track signal saturation
        if motors_enabled and abs(signal) > 0.9:
            signal_change_counter += config['loop_interval'] # ms
            if signal_change_counter > 1500:
                signal_change_counter = 0
                motors_enabled = False
                # retry enabling motors after short delay
                Timer(-1).init(mode=Timer.ONE_SHOT, period=2000, callback=lambda t: reset_control())
        else:
            signal_change_counter = 0

        # motor control
        if motors_enabled:
            servo1_PWM.duty_ns(int((1.5 + signal * 1.0) * 1000000))
            servo2_PWM.duty_ns(int((1.5 - signal * 1.0) * 1000000))
        else:
            servo1_PWM.duty_ns(0)
            servo2_PWM.duty_ns(0)
        #led_external_PWM.duty_u16(min(65535, round(abs(signal) * 65535.0)))

        # measure and track heading
        angular_accel = IMU.get_gyro()
        heading += (angular_accel[config['vert_axis']] + 0.5) * (config['loop_interval'] / 1000.0)
        heading = math.fmod(heading, 360.0)

        # send status info to laptop periodically
        if ble.is_connected() and config['status_send_period'] > 0:
            if ticks_diff(ticks_ms(), prev_status_time) > config['status_send_period']:
                prev_status_time = ticks_ms()
                bat = read_battery_percentage()
                data = {'a': accel, 'g': angular_accel, 't': IMU.get_temperature(), 's': filtered_angle, 
                        'h': heading, 'dt': dt, 'b': bat}
                ble.send(json.dumps(data))

        # dump measurement into csv file if needed
        if motors_enabled and data_file:
            data_file.write("{:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}\n".format(
                t1 / 1_000_000.0, 
                accel['x'], accel['y'], accel['z'], 
                angular_accel['x'], angular_accel['y'], angular_accel['z']
            ))


        t2 = ticks_us()
        dt = ticks_diff(t2, t1)

        sleep_us(max(10, config['loop_interval'] * 1000 - dt))

        # terminate when the button is pressed
        if not start_btn.value() and ticks_diff(ticks_ms(), last_btn_press) > 2000:
            quit_flag = True

    except (Exception, KeyboardInterrupt) as e:
        print("Exception in main loop: ", e)
        break
#end while

if data_file:
    data_file.close()
    print("Closed data.csv")

servo1_PWM.duty_ns(0)
servo2_PWM.duty_ns(0)

sleep_us(2_000_000)

blink_timer.deinit()
led_builtin.off()

ble.deactivate()
print("Finished")