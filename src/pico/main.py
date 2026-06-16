from utime import sleep, sleep_us, ticks_ms, ticks_us, ticks_diff
from control import PIDController, limit
from robot import BalancerBot, SlidingAverage
import json, math

sleep(1.5)

# controller for balancing
pitch_control = PIDController()
# controller for horizontal position
travel_control = PIDController()
# controller for heading direction or turning
heading_control = PIDController()

def on_config_load(config):
    pitch_control.configure(config['pid0'])
    travel_control.configure(config['pid1'])
    heading_control.configure(config['pid2'])

bot = BalancerBot(on_config_load)

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
            travel_control.configure(params)
        elif params.get('type') == 'pid2':
            heading_control.configure(params)
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
            bot.start_logging(['time', 'pitch', 'gyro', 'control', 'motor_position'], duration=5)
            log_pending = True
    except (json.JSONDecodeError, KeyError) as e:
        print("Unhandled BLE message: ", msg)
#end ble_msg_callback

bot.startBLE(ble_msg_callback)

bot.startIMU()

def reset_control():
    global motor_traversal, motor_signal
    bot.motors_enabled = True
    pitch_control.err_integral = 0.0
    motor_traversal = 0.0
    motor_signal = 0.0
    bot.heading = 0.0

prev_status_time = ticks_ms()
tick_duration = 0
max_tick_duration = 0
signal_change_counter = 0
log_pending = False

pitch_angle = SlidingAverage(bot.config['pitch_filter'])
pitch_deriv = SlidingAverage(bot.config['gyro_filter'])
motor_traversal = 0.0
motor_signal = 0.0

# main loop
while not bot.quit_flag:
    try:
        t1 = ticks_us()

        # timestep in seconds
        dt = bot.config['loop_interval'] / 1000.0
        pitch_offset = bot.config['pid0']['target']

        bot.updateIMU()

        # sensor measurements
        accel = bot.IMU.get_accel()
        gyro = bot.IMU.get_gyro()

        a = accel[bot.config['horiz_axis']]
        b = accel[bot.config['vert_axis']]
        omega = gyro[bot.config['pitch_axis']]

        signal_pitch, signal_yaw = 0.0, 0.0

        if b != 0:  # check we have actual measurements ready
            g_angle = math.degrees(math.atan(a / b))
            pitch_angle.add(g_angle, bot.config['pitch_filter'])
            pitch_deriv.add(omega, bot.config['gyro_filter'])

            # enable motors when first lifted to balance position
            if not bot.motors_enabled and abs(pitch_angle.get() - pitch_offset) < 1.0:
                reset_control()

            # control signal from pitch angle
            if abs(g_angle) > bot.config['pitch_limit']:
                bot.motors_enabled = False
            else:
                #pitch_control.target_value = pitch_offset - travel_control.calcPID(bot.speed.get(), dt)
                pitch_control.target_value = pitch_offset - travel_control.calcPID(motor_traversal, dt)
                signal_pitch = pitch_control.calcPID(pitch_angle.get(), dt, -pitch_deriv.get() if bot.config['use_gyro_as_D'] else None)
                signal_yaw = heading_control.calcPID(bot.heading, dt)

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

        # apply input to motors
        if bot.motors_enabled:
            motor_signal = limit(motor_signal + signal_pitch, 1.0)
            left_motor_signal =  limit(motor_signal - signal_yaw, 1.0)
            right_motor_signal = limit(motor_signal + signal_yaw, 1.0)
            motor_traversal += (left_motor_signal + right_motor_signal) / 2 * dt  # estimate integral of motor rotation
        else:
            left_motor_signal, right_motor_signal = 0.0, 0.0
        bot.motor_input(left_motor_signal, right_motor_signal)

        # send status info to laptop periodically
        if bot.config['status_send_period'] > 0 and ticks_diff(ticks_ms(), prev_status_time) > bot.config['status_send_period']:
            prev_status_time = ticks_ms()
            bot.send_status({'s': pitch_angle.get(), 'st': pitch_control.target_value,
                             'dt': max_tick_duration, 'mt': bot.speed.get()})
            max_tick_duration = 0

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
            bot.log([bot.time_ms() / 1000.0, pitch_angle.get(), pitch_deriv, signal_pitch, motor_traversal])
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

bot.motor_input(0,0) # stop motors
print("Terminated")

sleep(2.0)

bot.off()