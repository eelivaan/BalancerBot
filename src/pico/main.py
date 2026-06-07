from machine import Pin
from utime import sleep_us, sleep, ticks_ms, ticks_us, ticks_diff
from control import PIDController
from robot import BalancerBot
import json, math

PID = PIDController()

def on_config_load(config):
    PID.Kp = config['Kp']
    PID.Ki = config['Ki']
    PID.Kd = config['Kd']
    PID.target_value = config['target']

bot = BalancerBot(on_config_load)

# wait button press to start execution
#print("Press button to start...")
#bot.wait_button_press()

bot.startBlink()

def reset_control():
    bot.motors_enabled = True
    PID.err_integral = 0.0

def ble_msg_callback(msg):
    print("Received BLE message")
    try:
        params = json.loads(msg)
        # update PID params
        if params.get('type') == 'pid':
            PID.Kp = params['Kp']
            PID.Ki = params['Ki']
            PID.Kd = params['Kd']
            PID.target_value = params['tgt']
            PID.err_integral = 0.0
            bot.motors_enabled = params['en']
        # download config file
        elif params.get('type') == 'config':
            with open("config.json", "w") as f:
                f.write(params['content'])
            bot.load_config()  # Reload config to apply changes
        elif params.get('type') == 'quit':
            bot.quit_flag = True
    except (json.JSONDecodeError, KeyError) as e:
        print("Unhandled BLE message: ", msg)

bot.startBLE(ble_msg_callback)

data_file = None # open("data.csv", "w")
if data_file:
    data_file.write("time, ax,ay,az, gx,gy,gz\n")
    print("Opened data.csv")

bot.startIMU()

prev_status_time = ticks_ms()
tick_duration = 0
signal_change_counter = 0
prev_omega = 0.0

while not bot.quit_flag:
    try:
        t1 = ticks_us()

        bot.updateIMU()
        
        # timestep in seconds
        dt = bot.config['loop_interval'] / 1000.0

        # measure pitch angle
        accel = bot.IMU.get_accel()
        gyro = bot.IMU.get_gyro()
        
        # angular velocity around wheel axis
        omega = math.radians(gyro[bot.config['pitch_axis']])
        Domega = (omega - prev_omega) / dt
        prev_omega = omega
        r = 0.04  # 4 cm

        a = accel[bot.config['horiz_axis']] * 9.81 - Domega * r
        b = accel[bot.config['vert_axis']] * 9.81 - omega**2 * r
        pitch_angle = math.degrees(math.atan(a / b)) if b != 0 else 0

        if abs(pitch_angle) > bot.config['limit']:
            signal = 0.0
        else:
            signal = PID.calcPID(pitch_angle, dt)
            signal = max(signal, -1.0) if signal < 0 else min(signal, 1.0)

        # track signal saturation
        if bot.motors_enabled and abs(signal) > 0.9:
            signal_change_counter += bot.config['loop_interval'] # ms
            if signal_change_counter > bot.config['signal_cutoff_ms']:
                signal_change_counter = 0
                bot.motors_enabled = False
                # retry enabling motors after short delay
                #Timer(-1).init(mode=Timer.ONE_SHOT, period=2000, callback=lambda t: reset_control())
        else:
            signal_change_counter = 0

        bot.motor_input(signal)

        # send status info to laptop periodically
        if bot.config['status_send_period'] > 0 and ticks_diff(ticks_ms(), prev_status_time) > bot.config['status_send_period']:
            prev_status_time = ticks_ms()
            bot.send_status(pitch_angle, tick_duration)

        # dump measurement into csv file if needed
        #if bot.motors_enabled and data_file:
        #    data_file.write("{:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}\n".format(
        #        t1 / 1_000_000.0, 
        #        accel['x'], accel['y'], accel['z'], 
        #        angular_accel['x'], angular_accel['y'], angular_accel['z']
        #    ))

        t2 = ticks_us()
        tick_duration = ticks_diff(t2, t1)

        sleep_us(max(10, bot.config['loop_interval'] * 1000 - tick_duration))

        # toggle motors when button is pressed
        if bot.button_pressed():
            if not bot.motors_enabled:
                reset_control()
            else:
                bot.motors_enabled = False
                # terminate
                bot.quit_flag = True

    except (Exception, KeyboardInterrupt) as e:
        print("Exception in main loop: ", e)
        break
#end while

if data_file:
    data_file.close()
    print("Closed data.csv")

bot.motor_input(0) # stop motors

sleep_us(2_000_000)

bot.off()