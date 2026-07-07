MPY_DIR = ../../../micropython-v1.28.0

# Root of the Raspberry Pi Pico SDK. Override on the command line if needed.
PICO_SDK_PATH ?= /mnt/c/users/eeli/.pico-sdk/sdk/2.2.0

$(info PICO_SDK_PATH=$(PICO_SDK_PATH))

# Name of module
MOD = VL53L7CX

# Source files (.c or .py)
SRC = MPY_wrapper.cpp vl53l7cx_api.cpp vl53l7cx_platform.cpp

ARCH = armv7m

# not needed maybe?
BOARD = RPI_PICO2_W

# Include to get the rules for compiling and linking the module
#include $(MPY_DIR)/py/dynruntime.mk

# Added c++ support
include dynruntime-cpp.mk
