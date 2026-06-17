from machine import I2C, Pin
from icm20948 import QwiicIcm20948, acc_d50bw4_n68bw8, acc_d23bw9_n34bw4 
from VL53L4CX import VL53L4CX
from BLESerial import BLESerial # type: ignore
import time, math

led_builtin = Pin("LED", Pin.OUT)
led_builtin.on()

i2c0 = I2C(0, scl=Pin("GP21"), sda=Pin("GP20"), freq=400000)
print("I2C0 Scan result: ", end='')
for addr in i2c0.scan():
    print(hex(addr))

i2c1 = I2C(1, scl=Pin("GP7"), sda=Pin("GP6"), freq=400000)
print("I2C1 Scan result: ", end='')
for addr in i2c1.scan():
    print(hex(addr))

ToF_sensor = VL53L4CX(i2c1)

# OPTIONAL: can set non-default values
ToF_sensor.distance_mode = 2
ToF_sensor.timing_budget = 100

print("VL53L4CX Simple Test.")
print("--------------------")
model_id, module_type, mask_rev = ToF_sensor.model_info
print(f"Model ID: 0x{model_id:0X}")
print(f"Module Type: 0x{module_type:0X}")
print(f"Mask Revision: 0x{mask_rev:0X}")
print("Distance Mode: ", end="")
if ToF_sensor.distance_mode == 1:
    print("SHORT")
elif ToF_sensor.distance_mode == 2:
    print("LONG")
else:
    print("UNKNOWN")
print(f"Timing Budget: {ToF_sensor.timing_budget}")
print("--------------------")

ToF_sensor.start_ranging()

IMU = QwiicIcm20948(i2c0)

b = IMU.begin()
if not b:
    print("IMU initialization unsuccessful")
    raise KeyboardInterrupt

run = True
def on_notify(message):
    global run
    if message == "stop":
        run = False
ble_serial = BLESerial(on_notify)

IMU.enableDlpfAccel(True)
IMU.setDLPFcfgAccel(acc_d23bw9_n34bw4)
while run:
    try:
        if ToF_sensor.data_ready:
            #print(f"Dist: {ToF_sensor.distance} cm, Sig: {ToF_sensor.sigma} cm, Stat: {ToF_sensor.range_status}")
            ble_serial.send(f"0 Dist: {ToF_sensor.distance} cm, Sig: {ToF_sensor.sigma} cm, Stat: {ToF_sensor.range_status}")
            ToF_sensor.clear_interrupt()
        else:
            print("Waiting for VL53L4CX data")
            #time.sleep(0.3)

        if IMU.dataReady():
            IMU.getAgmt() # read all axis and temp from sensor, note this also updates all instance variables
            ax = IMU.axRaw / 16384.0
            ay = IMU.ayRaw / 16384.0
            az = IMU.azRaw / 16384.0
            pitch = math.degrees( math.atan(az / ay) ) if az != 0 else 0
            mx = IMU.mxRaw
            my = IMU.myRaw
            mz = IMU.mzRaw
            #print(f"ax: {ax:.3f} ay: {ay:.3f} az: {az:.3f}\tpitch: {pitch:.3f}\nmx: {mx} my: {my} mz: {mz}")
            ble_serial.send(f"1 ax: {ax:.3f} ay: {ay:.3f} az: {az:.3f}")
            ble_serial.send(f"2 pitch: {pitch:.3f}")
            ble_serial.send(f"3 mx: {mx} my: {my} mz: {mz}")
        else:
            print("Waiting for IMU data")
            time.sleep(0.3)

        time.sleep(0.2)
    except KeyboardInterrupt:
        break

ToF_sensor.stop_ranging()
ble_serial.deactivate()
led_builtin.off()