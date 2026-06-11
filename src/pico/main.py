from utime import sleep, sleep_us, ticks_ms, ticks_us, ticks_diff
from control import PIDController
from robot import BalancerBot, sign
import json, math

sleep(1.5)

# controller for balancing
pitch_control = PIDController()
# controller for horizontal position
target_control = PIDController()

def on_config_load(config):
    pitch_control.configure(config['pid0'])
    target_control.configure(config['pid1'])

bot = BalancerBot(on_config_load)

# wait button press to start execution
#print("Press button to start...")
#bot.wait_button_press()

bot.startBlink()

def ble_msg_callback(msg):
    global pitch_angle, log_pending
    print("Received BLE message")
    try:
        params = json.loads(msg)
        # update PID params
        if params.get('type') == 'pid0':
            pitch_control.configure(params)
            bot.config['pid0']['target'] = params['target']
            bot.motors_enabled = params['en']
        elif params.get('type') == 'pid1':
            target_control.configure(params)
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
        elif params.get('type') == 'log':
            bot.start_logging(['time', 'pitch', 'control', 'motor_position'], duration=5)
            log_pending = True
    except (json.JSONDecodeError, KeyError) as e:
        print("Unhandled BLE message: ", msg)

bot.startBLE(ble_msg_callback)

bot.startIMU()

def reset_control():
    global motor_traversal, motor_signal
    bot.motors_enabled = True
    pitch_control.err_integral = 0.0
    motor_traversal = 0.0
    motor_signal = 0.0

prev_status_time = ticks_ms()
tick_duration = 0
max_tick_duration = 0
signal_change_counter = 0
log_pending = False

#prev_omega = 0.0
pitch_angle = None
pitch_history = []
motor_traversal = 0.0
motor_signal = 0.0

while not bot.quit_flag:
    try:
        t1 = ticks_us()

        # timestep in seconds
        dt = bot.config['loop_interval'] / 1000.0
        pitch_offset = bot.config['pid0']['target']

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
                #acc_delta_angle = g_angle - pitch_angle
                #gyro_delta_angle = gyro[bot.config['pitch_axis']] * dt
                #clamped_delta = sign(acc_delta_angle) * min(abs(acc_delta_angle), abs(gyro_delta_angle))
                #pitch_angle += clamped_delta
                if bot.config['pitch_filter'] > 1:
                    pitch_history.append(g_angle)
                    while len(pitch_history) > bot.config['pitch_filter']:
                        pitch_history.pop(0)
                    pitch_angle = sum(pitch_history) / len(pitch_history)
                else:
                    pitch_angle = g_angle

                # enable motors when first lifted to balance position
                if not bot.motors_enabled and abs(pitch_angle - pitch_offset) < 1.0:
                    reset_control()

            # control signal from pitch angle
            if abs(pitch_angle) > bot.config['pitch_limit']:
                signal = 0.0
                bot.motors_enabled = False
            else:
                pitch_control.target_value = pitch_offset + target_control.calcPID(motor_traversal, dt)
                signal = pitch_control.calcPID(pitch_angle, dt)
                signal = sign(signal) * math.pow(min(1.0, abs(signal)), bot.config['signal_power'])
        else:
            signal = 0.0

        # track signal saturation
        if bot.motors_enabled and abs(motor_signal) > 0.9:
            signal_change_counter += bot.config['loop_interval'] # ms
            if signal_change_counter > bot.config['signal_cutoff_ms']:
                signal_change_counter = 0
                bot.motors_enabled = False
                # retry enabling motors after short delay
                #Timer(-1).init(mode=Timer.ONE_SHOT, period=2000, callback=lambda t: reset_control())
        else:
            signal_change_counter = 0

        if bot.motors_enabled:
            motor_signal += signal
            motor_signal = sign(motor_signal) * min(1.0, abs(motor_signal))
        bot.motor_input(motor_signal)
        motor_traversal -= motor_signal * dt  # estimate integral of motor rotation

        # send status info to laptop periodically
        if bot.config['status_send_period'] > 0 and ticks_diff(ticks_ms(), prev_status_time) > bot.config['status_send_period']:
            bot.send_status(pitch_angle, max_tick_duration, pitch_control.target_value)
            max_tick_duration = 0
            prev_status_time = ticks_ms()

        # quit when button is pressed
        if bot.button_pressed():
            bot.motors_enabled = False
            # terminate
            bot.quit_flag = True

        t2 = ticks_us()
        tick_duration = ticks_diff(t2, t1)
        max_tick_duration = max(tick_duration, max_tick_duration)

        sleep_us(max(10, bot.config['loop_interval'] * 1000 - tick_duration))

        # log if needed
        if bot.logging():
            bot.log([bot.time_ms() / 1000.0, pitch_angle, signal, motor_traversal])
        elif log_pending:
            log_pending = False
            bot.ble.send('log_output') # type: ignore
            with open('log.csv', 'r') as f:
                for line in f:
                    bot.ble.send(line) # type: ignore
            bot.ble.send('log_end') # type: ignore

    except (Exception, KeyboardInterrupt) as e:
        print("Exception in main loop: ", e)
        break
#end while

bot.motor_input(0) # stop motors
print("Terminated")

sleep(2.0)

bot.off()