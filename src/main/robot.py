"""
Interface for the robot
"""
from machine import Pin, ADC, PWM, I2C, Timer
from icm20948 import QwiicIcm20948
from VL53L7CX import VL53L7CX
from BLESerial import BLESerial
from sound import Speaker
import json, math, time

def sign(x):
    return 0 if x == 0 else (1 if x > 0 else -1)

def wrap_angle(x):
    """ Keep angle between -180 and +180 assuming it's never outside 360 range """
    if x > 180:
        return -360.0 + x
    elif x < -180:
        return 360.0 + x
    return x

class SlidingAverage:
    """ Simple sliding average implementation """
    
    def __init__(self, length: int) -> None:
        self.set(0.0, length)

    def set(self, value: float, length=None):
        if length is None:
            length = len(self.samples)
        self.samples = [value for i in range(length)]
        self.sample_index = 0
        self.average = value

    def add(self, value: float, length=None):
        if length is None:
            length = len(self.samples)
        elif length != len(self.samples):
            self.set(0.0, length)
        self.average -= self.samples[self.sample_index] * (1.0 / length)
        self.samples[self.sample_index] = value
        self.average += value * (1.0 / length)
        self.sample_index = (self.sample_index + 1) % length

    def get(self) -> float:
        return self.average
#end SlidingAverage


class BalancerBot:
    def __init__(self, config_load_callback=None):
        self.led_builtin = Pin("LED", Pin.OUT)
        self.led_builtin.on()
        self.blink_timer = None

        self.bat_adc = ADC(Pin("GP26"))

        self.config = {}
        self.config_load_cb = config_load_callback
        self.load_config()

        # motors
        self.servoL_PWM = PWM(Pin(self.config['left_motor_pin']), freq=50)
        self.servoR_PWM = PWM(Pin(self.config['right_motor_pin']), freq=50)

        # inertial motion unit
        self.IMU_i2c = I2C(0, scl=Pin(self.config['IMU_scl_pin']), 
                              sda=Pin(self.config['IMU_sda_pin']), freq=400000)
        addresses = self.IMU_i2c.scan()
        print("I2C0 Scan result:", [hex(ad) for ad in addresses])
        if len(addresses):
            self.IMU = QwiicIcm20948(self.IMU_i2c, addresses[0])
        else:
            print("IMU I2C not found")
            #self.IMU = None
            self.quit_flag = True

        # 8x8 time-of-flight sensor
        self.ToF_i2c = I2C(1, scl=Pin(self.config['ToF_scl_pin']),
                              sda=Pin(self.config['ToF_sda_pin']), freq=400000)
        #addresses = self.ToF_i2c.scan()
        #print("I2C1 Scan result:", [hex(ad) for ad in addresses])
        #if len(addresses):
        #    self.ToF_sensor = VL53L4CX(self.ToF_i2c)
        #else:
        #    print("ToF I2C not found")
        #    self.ToF_sensor = None
        try:
            self.ToF_sensor = VL53L7CX(self.ToF_i2c, self.config['ToF_lpn_pin'])
            self.ToF_sensor.configure(self.config['ToF_resolution'], self.config['ToF_frequency'])
        except Exception as e:
            print("Failed to init 8x8 VL53L7CX sensor: ", e)
            self.ToF_sensor = None

        # external button
        self.button = Pin(self.config['button_pin'], Pin.IN, Pin.PULL_UP)
        self.button_pressed_flag = False

        # speaker
        self.speaker = Speaker(self.config['speaker_pin'])
        self.speaker.volume(self.config['speaker_volume'])

        # BLE off by default
        self.ble = None

        self.heading = 0.0      # heading angle 0-359
        self.travel = 0.0       # horizontal travel in undefined units
        self.headingsum = 0.0   # total change of heading
        self.angularv = 0.0     # angular velocity around pitch axis
        self.speed = SlidingAverage(self.config['speed_filter'])        # filtered speed value
        self.pitch_angle = SlidingAverage(self.config['pitch_filter'])  # filtered pitch angle
        self.pitch_deriv = SlidingAverage(self.config['gyro_filter'])   # filtered pitch derivative (filtered angularv)
        self.motors_enabled = True
        self.motor_speed = 0.0      # instantaneous motor speed
        self.quit_flag = False
        self.logfile = None
        self.last_depth_measurement = []
        self.RC_on = False

        self.last_ticks = time.ticks_ms()
        self.internal_time = 0
    #end __init__


    def load_config(self):
        with open('config.json', 'r') as f:
            self.config = json.load(f)
            if self.config_load_cb:
                self.config_load_cb(self.config)


    def startBlink(self, period=400):
        self.blink_timer = Timer(-1)
        self.blink_timer.init(period=period, callback=lambda t: self.led_builtin.toggle())


    def startIMU(self):
        if self.IMU and self.IMU.begin():
            if self.config['accel_dlpf'] == -1:
                self.IMU.enableDlpfAccel(False)
            else:
                self.IMU.enableDlpfAccel(True)
                self.IMU.setDLPFcfgAccel(self.config['accel_dlpf'])
                
            if self.config['gyro_dlpf'] == -1:
                self.IMU.enableDlpfGyro(False)
            else:
                self.IMU.enableDlpfGyro(True)
                self.IMU.setDLPFcfgGyro(self.config['gyro_dlpf'])
            self.IMU_start_time = time.ticks_ms()
            self.IMU_last_update_time = -1
        else:
            print("IMU initialization failed")
            self.quit_flag = True

    
    def startToF(self):
        if self.ToF_sensor:
            self.ToF_sensor.start_ranging()
            return True
        else:
            return False
            

    def startBLE(self, ble_msg_callback):
        self.ble = BLESerial(ble_msg_callback)


    def beep(self, pattern=[440.0], blocking=False):
        """ Make a series of 0.15 second beeps asynchronously """
        self.speaker.beep(pattern[0], 0.15)
        for i in range(1, len(pattern)):
            Timer(-1, mode=Timer.ONE_SHOT, period=200*i, callback=lambda t: self.speaker.beep(pattern[i], 0.15))
        if blocking:
            time.sleep_ms(len(pattern) * 200)
    
    
    def read_battery_voltage(self):
        raw = self.bat_adc.read_u16()
        return raw / 65535.0 * 3.3 * 2


    def read_battery_percentage(self):
        return round((self.read_battery_voltage() - 3.40) / (4.00 - 3.40) * 100)
    

    def wait_button_press(self):
        while self.button.value(): time.sleep(0.1)
        self.button_pressed_flag = False


    def button_pressed(self):
        if not self.button.value():
            self.button_pressed_flag = True
            return False
        elif self.button_pressed_flag:
            self.button_pressed_flag = False
            return True
        return False
    

    def time_ms(self):
        now = time.ticks_ms()
        self.internal_time += time.ticks_diff(now, self.last_ticks)
        self.last_ticks = now
        return self.internal_time


    def motor_input(self, left_signal, right_signal):
        # motor control
        if self.motors_enabled:
            pulse = sign(left_signal) * (self.config['motor_PWM_min'] + abs(left_signal) * 100)
            self.servoL_PWM.duty_ns(int((150 + pulse) * 10000))
            pulse = sign(right_signal) * (self.config['motor_PWM_min'] + abs(right_signal) * 100)
            self.servoR_PWM.duty_ns(int((150 - pulse) * 10000))
            self.speed.add((left_signal + right_signal) / 2.0, self.config['speed_filter'])
            self.motor_speed = (left_signal + right_signal) / 2
        else:
            self.servoL_PWM.duty_ns(0)
            self.servoR_PWM.duty_ns(0)
            self.speed.set(0.0)
            self.motor_speed = 0.0


    def send_status(self, custom_data):
        if self.ble and self.ble.is_connected():
            bat = self.read_battery_voltage()
            if self.RC_on:
                # send different data when remote controlling
                data = {'h': self.heading, 'mt': self.speed.get(), 'b': bat, 'sd': self.config['stop_distance_cm'], 
                        'dimg': self.last_depth_measurement, 'dt': custom_data['dt']}
            else:
                data = {'a': self.IMU.get_accel(), 'g': self.IMU.get_gyro(), 'm': self.IMU.get_mag(),  # type: ignore
                        't': self.IMU.get_temperature(), 'h': self.heading, 'b': bat,
                        's': self.pitch_angle.get(), 'mt': self.speed.get()}
                data.update(custom_data)  # append custom data
            self.ble.send(json.dumps(data))


    def update(self, dt: float):
        if self.IMU and self.IMU.dataReady():
            # read all axis and temp from sensor, note this also updates all instance variables
            self.IMU.getAgmt()
            # track heading
            heading_delta = self.IMU.get_gyro()[self.config['vert_axis']] * dt
            self.heading = wrap_angle(self.heading + heading_delta)
            self.headingsum += heading_delta
            # track time
            self.IMU_last_update_time = time.ticks_diff(time.ticks_ms(), self.IMU_start_time) / 1000.0

        # sensor measurements
        accel = self.IMU.get_accel()
        gyro = self.IMU.get_gyro()
        a = accel[self.config['horiz_axis']]    # one side of triangle
        b = accel[self.config['vert_axis']]     # other side of triangle
        self.angularv = gyro[self.config['pitch_axis']] # angular velocity around pitch axis
        if b != 0:  # check we have actual measurements ready
            self.g_angle = math.degrees(math.atan(a / b))    # angle of gravity vector
            self.pitch_angle.add(self.g_angle, self.config['pitch_filter'])
            self.pitch_deriv.add(self.angularv, self.config['gyro_filter'])

        if self.ToF_sensor and self.ToF_sensor.is_data_ready():
            if depthimg := self.ToF_sensor.get_ranging_data():
                self.last_depth_measurement = depthimg

        # keep track of travel distance
        self.travel += self.motor_speed * dt  # estimate integral of motor rotation
    #end update


    def off(self):
        self.quit_flag = True
        self.motor_input(0,0)

        if self.logging():
            self.stop_logging()
        
        if self.blink_timer:
            self.blink_timer.deinit()
        self.led_builtin.off()

        if self.ToF_sensor:
            self.ToF_sensor.stop_ranging()
            self.ToF_sensor.destroy()

        if self.ble:
            self.ble.deactivate()
        print("Finished")
    #end off


# -------------------------------------------------- logging --------------------------------------------------
    def start_logging(self, fields: list[str], logname='log', duration=5):
        self.logfile = open(logname + '.csv', 'w')
        if self.logfile:
            self.logfile.write(','.join(fields) + '\n')
            self.log_end_time = time.time() + min(duration, 10)
            print("Started logging for", duration, "seconds")
            return True
        else:
            return False

    def log(self, values: list):
        if self.logging():
            self.logfile.write(','.join(str(v) for v in values) + '\n') # type: ignore
            return True
        else:
            return False
        
    def logging(self):
        if self.logfile and time.time() > self.log_end_time:
            self.stop_logging()
            return False
        return self.logfile != None
        
    def stop_logging(self):
        if self.logfile:
            self.logfile.close()
            self.logfile = None
            print("Stopped logging")
            return True
        else:
            return False

    # --------------------------------------------- for plotting purposes ---------------------------------------------
    def measure_accel_with_time(self):
        v = self.IMU.get_accel() # type: ignore
        v['t'] = self.IMU_last_update_time
        return v

    def measure_gyro_with_time(self):
        v = self.IMU.get_gyro() # type: ignore
        v['t'] = self.IMU_last_update_time
        return v

    def measure_mag_with_time(self):
        v = self.IMU.get_mag() # type: ignore
        v['t'] = self.IMU_last_update_time
        return v


