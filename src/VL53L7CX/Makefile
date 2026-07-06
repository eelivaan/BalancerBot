MPY_DIR = ../../../raspberry-pico/micropython-v1.28.0

# Name of module
MOD = VL53L7CX

# Source files (.c or .py)
SRC = MPY_wrapper.cpp vl53l7cx_api.cpp vl53l7cx_platform.cpp

ARCH = armv7m

# not needed maybe?
BOARD = RPI_PICO2_W

#include ../pico-sdk-import/Makefile

# Include to get the rules for compiling and linking the module
#include $(MPY_DIR)/py/dynruntime.mk

# Added c++ support
include dynruntime-cpp.mk