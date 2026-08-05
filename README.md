## About

A two-wheeled robot that uses PID-controller with accelerometer and gyroscope data to stay in balance. 
The project also features desktop user interfaces for tuning the PID parameters wirelessly and for remote control.

<video width="400" src="https://github.com/user-attachments/assets/d2c598fd-b4f8-46e6-aca9-dc9cf0eea812"></video>

## Program flow

1. Power on with switch -> 1.5 s delay -> led lit up
2. Led starts flashing  -> Bot in idle mode <strong>(BLE active)</strong>
3. Lift into balance position by hand or run ```RemoteControl.py``` -> Bot in balancing mode <strong>(BLE active)</strong>
4. Press on-board button or terminate from UI -> Bot connects to local network and goes into file transfer mode <strong>(BLE inactive, WLAN active)</strong>
5. Connect ```http://10.76.162.118:2323``` via browser or via ```TCP_client.py``` to upload/download files <strong>(WLAN active)</strong>
6. Press on-board button or send QUIT command to shutdown or send BOOT command to restart from 2. <strong>(WLAN inactive)</strong>
7. Power off with switch

## UI dependencies

```bash
pip install bleak numpy matplotlib opencv-python pillow
```
