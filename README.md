## About

A two-wheeled robot that uses PID-controller with accelerometer and gyroscope data to stay in balance. 
The project also features desktop user interfaces for tuning the PID parameters wirelessly and for remote control.
The source code is Micropython extended with some custom c++ modules that are frozen into the binary.

<video src="https://github.com/user-attachments/assets/4853bf55-4256-4b5c-aa26-172c8961ecdb"></video>

## Control options

- BLE remote control from desktop
- Follow a predefined path
- Follow hand or other target that is kept in its field of view

## Program flow

1. Power on switch ⟶ 1 s delay ⟶ led lits up
2. Led starts flashing ⟶ Bot in idle mode <strong>(BLE active)</strong>
3. Lift into balance position by hand or run ```RemoteControl.py``` ⟶ Bot in active balancing mode <strong>(BLE active)</strong>
4. Press on-board button or terminate from UI ⟶ Bot stops balancing, connects to local network and goes into file transfer mode <strong>(BLE inactive, WLAN active)</strong>
5. Connect ```http://<ip>:2323``` via browser or via ```TCP_client.py``` to upload/download files wirelessly <strong>(WLAN active)</strong>
6. Press on-board button or send QUIT command to shutdown, or send BOOT command to restart from 2. <strong>(WLAN inactive)</strong>
7. Power off switch

## UI dependencies

```bash
pip install bleak numpy matplotlib opencv-python pillow
```

## Native modules

1. Getting Micropython (into WSL folder):
    ```bash
    # using the latest stable release tag
    git clone --branch v1.29.0 --single-branch --sparse https://github.com/micropython/micropython.git
    cd micropython
    # git sparse-checkout init --cone
    git sparse-checkout set drivers extmod lib mpy-cross ports/rp2 py shared tools
    git checkout v1.29.0
    git submodule update --init --recursive
    ```
2. After modifications, run ```src/copy-native-modules.bat``` (Alt-V shortcut in VS Code) to copy the c/c++ source code next to micropython repository in WSL.
3. Build micropython with the custom modules freezed:

    ```bash
    cd micropython
    # When building the first time
    make -C mpy-cross
    cd ports/rp2
    make BOARD=RPI_PICO2_W submodules
    # Each time the module source is changed
    make BOARD=RPI_PICO2_W clean
    make BOARD=RPI_PICO2_W USER_C_MODULES=../../../modules/micropython.cmake # MICROPY_C_HEAP_SIZE=4096
    make BOARD=RPI_PICO2_W copy
    ```
4. Now the ```micropython.uf2``` binary is found under ```BalancerBot/bin/``` ready for deployment into Pico

(https://docs.micropython.org/en/latest/develop/cmodules.html)

<strong>TODO:</strong> https://docs.micropython.org/en/latest/develop/cmodules.html#specifying-c-modules-via-a-manifest