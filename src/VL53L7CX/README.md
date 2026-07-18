
Custom Micropython module for the VL53L7CX 8x8 time-of-flight sensor 
(c++ API from stm32duino, modified to use Pico SDK).

Three different approaches to deploy: 

## Freezing into Micropython firmware
1. Run ```freeze/copy-module.bat``` to copy the module into micropython tree
2. Build micropython:

    ```bash
    cd micropython
    # When building the first time
    make -C ports/rp2 BOARD=RPI_PICO2_W submodules
    make -C mpy-cross
    # Each time the module source is changed
    cd ports/rp2
    make BOARD=RPI_PICO2_W USER_C_MODULES=../../../../modules/micropython.cmake
    ```
3. Now the ```micropython.uf2``` binary is found under ```BalancerBot/bin/```

Uses ```module.cpp``` and make fragments at this directory.

https://docs.micropython.org/en/latest/develop/cmodules.html


## Building mpy binary file with CMake
```bash
# inside src/VL53L7CX/cmake/
cmake .
make
```
- CMake configuration combines custom mpy module Make workflow with Pico SDK workflow
- Expects micropython repo cloned into WSL ```$USERHOME/pico/micropython```
- *To be finalized*

Uses ```cmake/dynruntime-module.cpp``` as source.


## Building mpy binary file with Make
```bash
# inside src/VL53L7CX/make/
make
```
- ```dynruntime-cpp.mk```: added c++ support to ```micropython/py/dynruntime.mk```
- Works only if Pico SDK symbols are not needed

Uses ```cmake/dynruntime-module.cpp``` as source.

https://docs.micropython.org/en/latest/develop/natmod.html
