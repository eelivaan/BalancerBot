
Custom Micropython wrapper for the VL53L7CX 8x8 time-of-flight sensor 
(c++ API from stm32duino, modified to use Pico SDK)

### Building with CMake
- CMake configuration combines custom mpy module Make workflow with Pico SDK workflow
- Expects micropython repo cloned into WSL $USERHOME/pico/micropython

### Building with Make
- *dynruntime-cpp.mk*: added c++ support to *micropython/py/dynruntime.mk*
- Works only if Pico SDK symbols are not needed
