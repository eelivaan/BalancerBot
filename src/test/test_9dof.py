from machine import I2C, Pin
from icm20948 import QwiicIcm20948, acc_d50bw4_n68bw8, acc_d23bw9_n34bw4 
import time, math

i2c = I2C(0, scl=Pin("GP21"), sda=Pin("GP20"), freq=400000)
print("I2C Scan result: ", end='')
for addr in i2c.scan():
    print(hex(addr))

IMU = QwiicIcm20948(i2c)

b = IMU.begin()
if not b:
    print("IMU initialization unsuccessful")
else:
    IMU.enableDlpfAccel(True)
    IMU.setDLPFcfgAccel(acc_d23bw9_n34bw4 )
    while True:
        if IMU.dataReady():
            IMU.getAgmt() # read all axis and temp from sensor, note this also updates all instance variables
            ax = IMU.axRaw / 16384.0
            ay = IMU.ayRaw / 16384.0
            az = IMU.azRaw / 16384.0
            pitch = math.degrees( math.atan(ax / az) )
            mx = IMU.mxRaw
            my = IMU.myRaw
            mz = IMU.mzRaw
            print(f"ax: {ax:.3f} ay: {ay:.3f} az: {az:.3f}\tpitch: {pitch:.3f}\nmx: {mx} my: {my} mz: {mz}")
            #time.sleep(0.03)
            time.sleep(0.3)
        else:
            print("Waiting for data")
            time.sleep(0.5)
