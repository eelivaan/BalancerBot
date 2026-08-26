from utime import sleep, sleep_us, ticks_ms, ticks_us, ticks_diff
sleep(1.0) # let power stabilize before starting the actual work
from robot import BalancerBot
from statemachine import *
import json

bot = BalancerBot(on_config_load)

bot.startBlink()

bot.beep()

def ble_msg_callback(msg):
    """ Receive and handle BLE messages """
    global log_pending
    print("Received BLE message")
    try:
        params = json.loads(msg)
        t = params.get('type')
    # update PID params
        if t == 'pid0':
            pitch_control.configure(params)
            bot.config['pid0']['target'] = params['target']
        elif t == 'pid1':
            travel_control.configure(params)
        elif t == 'pid2':
            heading_control.configure(params)
        elif t == 'motors_en':
            bot.motors_enabled = params['en']
    # set config entry
        elif t == 'set_config':
            bot.config[params['key']] = params['value']
    # download config file
        elif t == 'config':
            with open("config.json", "w") as f:
                f.write(params['content'])
            bot.load_config()  # Reload config to apply changes
    # terminate
        elif t == 'quit':
            bot.quit_flag = True
    # calibrate IMU
        elif t == 'calibrate':
            bot.IMU.calibrate()
    # start logging
        elif t == 'log':
            bot.start_logging(['time', 'pitch', 'gyro', 'motor_position'], duration=5)
            log_pending = True
    # remote control
        elif t == 'rc_start':
            bot.RC_on = True
            stm.change_state(STATE_Raiseup())
        elif t == 'rc_move':
            stm.change_state(STATE_Driving(params['sp']))
        elif t == 'rc_turn':
            stm.change_state(STATE_Turning(params['sp']))
        elif t == 'rc_stop':
            stm.change_state(STATE_Balancing())
        elif t == 'rc_path':
            stm.change_state(STATE_FollowPath(params['path']))
        elif t == 'rc_end':
            bot.RC_on = False
            stm.change_state(STATE_Rest())

    except (json.JSONDecodeError, KeyError) as e:
        print("Unhandled BLE message: ", msg)
#end ble_msg_callback

bot.startBLE(ble_msg_callback)
bot.startIMU()
bot.startToF()

stm = StateMachine(bot)
stm.change_state(STATE_Rest())

prev_status_time = ticks_ms()
tick_duration_us, max_tick_duration = 0, 0
log_pending = False

# -- main loop --
while not bot.quit_flag:
    try:
        t1 = ticks_us()

        # timestep in seconds
        dt = 1.0 / bot.config['loop_frequency']

        # update sensors, status etc.
        bot.update(dt)

        # update state (sets motor input)
        stm.update(dt)

        # send status info to laptop periodically
        if bot.config['status_send_period'] > 0 and ticks_diff(ticks_ms(), prev_status_time) > bot.config['status_send_period']:
            prev_status_time = ticks_ms()
            bot.send_status({'st': pitch_control.target_value, 'dt': max_tick_duration, 'snm': stm.cur_state.__qualname__})
            max_tick_duration = 0

        # log if needed
        if bot.logging():
            bot.log([bot.time_ms() / 1000.0, bot.pitch_angle.get(), bot.pitch_deriv.get(), bot.travel.get()])
        elif log_pending:
            log_pending = False
            bot.ble.send('log_output') # type: ignore
            with open('log.csv', 'r') as f:
                for line in f:
                    bot.ble.send(line) # type: ignore
            bot.ble.send('log_end') # type: ignore
        #end if

        # quit when button is pressed
        if bot.button_pressed():
            # terminate
            bot.quit_flag = True

        # sleep excess time to match the wanted control loop frequency
        t2 = ticks_us()
        tick_duration_us = ticks_diff(t2, t1)
        max_tick_duration = max(tick_duration_us, max_tick_duration)

        sleep_us(max(10, 1_000_000 // bot.config['loop_frequency'] - tick_duration_us))

    except (Exception, KeyboardInterrupt) as e:
        print("Exception in main loop: ", e)
        break
#end while


bot.motor_input(0,0) # stop motors
bot.beep()
print("Terminated")

sleep(2.0)

bot.off()


# -- start filesystem control over WLAN --

from networking import run_tcp_server

run_tcp_server(stopcondition = lambda: bot.button_pressed())
