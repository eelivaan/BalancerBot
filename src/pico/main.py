from utime import sleep_us, ticks_ms, ticks_us, ticks_diff
from control import PIDController
from robot import BalancerBot, sign
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

def ble_msg_callback(msg):
    global pitch_angle
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
        elif params.get('type') == 'calibrate':
            bot.IMU.calibrate()
            pitch_angle = None
    except (json.JSONDecodeError, KeyError) as e:
        print("Unhandled BLE message: ", msg)

bot.startBLE(ble_msg_callback)

bot.startIMU()

def reset_control():
    bot.motors_enabled = True
    PID.err_integral = 0.0

prev_status_time = ticks_ms()
tick_duration = 0
signal_change_counter = 0

prev_omega = 0.0
pitch_angle = None

while not bot.quit_flag:
    try:
        t1 = ticks_us()

        # timestep in seconds
        dt = bot.config['loop_interval'] / 1000.0

        if bot.updateIMU():
            # measurements
            accel = bot.IMU.get_accel()
            gyro = bot.IMU.get_gyro()
            
            # angular velocity around wheel axis
            #omega = math.radians(gyro[bot.config['pitch_axis']])
            #Domega = (omega - prev_omega) / dt
            #prev_omega = omega
            #r = bot.config['IMU_offset']  # 4 cm

            a = accel[bot.config['horiz_axis']] #* 9.81 + Domega * r
            b = accel[bot.config['vert_axis']] #* 9.81 + omega**2 * r
            g_angle = math.degrees(math.atan(a / b)) if b != 0 else 0

            if pitch_angle == None:
                pitch_angle = g_angle
            else:
                acc_delta_angle = g_angle - pitch_angle

                gyro_delta_angle = gyro[bot.config['pitch_axis']] * dt

                #if sign(acc_delta_angle) != sign(gyro_delta_angle):
                #    clamped_delta = gyro_delta_angle
                #else:
                clamped_delta = sign(acc_delta_angle) * min(abs(acc_delta_angle), abs(gyro_delta_angle))
                pitch_angle += clamped_delta

            # control signal from pitch angle
            if abs(pitch_angle) > bot.config['limit']:
                signal = 0.0
            else:
                signal = PID.calcPID(pitch_angle, dt)
                signal = max(signal, -1.0) if signal < 0 else min(signal, 1.0) # clamp [-1 1]
        else:
            signal = 0.0

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

        # toggle motors when button is pressed
        if bot.button_pressed():
            if not bot.motors_enabled:
                reset_control()
                print("Motors active")
            else:
                bot.motors_enabled = False
                # terminate
                bot.quit_flag = True

        t2 = ticks_us()
        tick_duration = ticks_diff(t2, t1)

        sleep_us(max(10, bot.config['loop_interval'] * 1000 - tick_duration))

    except (Exception, KeyboardInterrupt) as e:
        print("Exception in main loop: ", e)
        break
#end while

bot.motor_input(0) # stop motors
print("Terminated")

sleep_us(2_000_000)

bot.off()