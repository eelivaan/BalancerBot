from machine import Pin, ADC, PWM, I2C, Timer
from icm20948 import QwiicIcm20948
from BLESerial import BLESerial
import json, math, time

def sign(x):
    return 0 if x == 0 else (1 if x > 0 else -1)

class BalancerBot:
    def __init__(self, config_load_callback=None):
        self.led_builtin = Pin("LED", Pin.OUT)
        self.led_builtin.on()
        self.blink_timer = None

        self.bat_adc = ADC(Pin("GP26"))

        self.config = {}
        self.config_load_cb = config_load_callback
        self.load_config()

        self.servoL_PWM = PWM(Pin(self.config['left_motor_pin']), freq=50)
        self.servoR_PWM = PWM(Pin(self.config['right_motor_pin']), freq=50)

        self.IMU_i2c = I2C(0, scl=Pin("GP21"), sda=Pin("GP20"), freq=400000)
        print("I2C Scan result: ", end='')
        for addr in self.IMU_i2c.scan():
            print(hex(addr))
        self.IMU = QwiicIcm20948(self.IMU_i2c)

        self.button = Pin("GP22", Pin.IN, Pin.PULL_UP)
        self.button_pressed_flag = False

        self.ble = None

        self.heading = 0.0
        self.motors_enabled = False
        self.quit_flag = False
        self.logfile = None

        self.last_ticks = time.ticks_ms()
        self.internal_time = 0


    def load_config(self):
        with open('config.json', 'r') as f:
            self.config = json.load(f)
            if self.config_load_cb:
                self.config_load_cb(self.config)


    def startBlink(self, period=400):
        self.blink_timer = Timer(-1)
        self.blink_timer.init(period=period, callback=lambda t: self.led_builtin.toggle())


    def read_battery_percentage(self):
        raw = self.bat_adc.read_u16()
        if raw < 10:
            return -1
        voltage = raw / 65535.0 * 3.3 * 2
        return round((voltage - 3.40) / (4.00 - 3.40) * 100)
    

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
    

    def startIMU(self):
        if self.IMU.begin():
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
            print("IMU initialization unsuccessful")
            self.quit_flag = True

    
    def updateIMU(self):
        if self.IMU.dataReady():
            self.IMU.getAgmt() # read all axis and temp from sensor, note this also updates all instance variables
            # track heading
            self.heading += self.IMU.get_gyro()[self.config['vert_axis']] * (self.config['loop_interval'] / 1000.0)
            self.heading = math.fmod(self.heading, 360.0)
            # track time
            self.IMU_last_update_time = time.ticks_diff(time.ticks_ms(), self.IMU_start_time) / 1000.0
            return True
        return False
    

    def measure_accel_with_time(self):
        v = self.IMU.get_accel()
        v['t'] = self.IMU_last_update_time
        return v

    def measure_gyro_with_time(self):
        v = self.IMU.get_gyro()
        v['t'] = self.IMU_last_update_time
        return v

    def measure_mag_with_time(self):
        v = self.IMU.get_mag()
        v['t'] = self.IMU_last_update_time
        return v


    def startBLE(self, ble_msg_callback):
        self.ble = BLESerial(ble_msg_callback)
    
    
    def motor_input(self, signal):
        # motor control
        if self.motors_enabled:
            pulse = sign(signal) * (self.config['motor_PWM_min'] + abs(signal) * 100)
            self.servoL_PWM.duty_ns(int((150 + pulse) * 10000))
            self.servoR_PWM.duty_ns(int((150 - pulse) * 10000))
        else:
            self.servoL_PWM.duty_ns(0)
            self.servoR_PWM.duty_ns(0)


    def send_status(self, pitch, dt, pitch_target):
        if self.ble and self.ble.is_connected():
            bat = self.read_battery_percentage()
            data = {'a': self.IMU.get_accel(), 'g': self.IMU.get_gyro(), 'm': self.IMU.get_mag(), 't': self.IMU.get_temperature(), 
                    's': pitch, 'st': pitch_target, 'h': self.heading, 'dt': dt, 'b': bat}
            self.ble.send(json.dumps(data))


    def time_ms(self):
        now = time.ticks_ms()
        self.internal_time += time.ticks_diff(now, self.last_ticks)
        self.last_ticks = now
        return self.internal_time


    def off(self):
        self.quit_flag = True
        self.motor_input(0)

        if self.logging():
            self.stop_logging()
        
        if self.blink_timer:
            self.blink_timer.deinit()
        self.led_builtin.off()

        if self.ble:
            self.ble.deactivate()
        print("Finished")


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