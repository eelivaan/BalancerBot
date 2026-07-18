MPY_DIR = /home/eeli/pico/micropython

# MPY_EXTERN_SYM_FILE = ../../../bin/micropython.elf

# Root of the Raspberry Pi Pico SDK. Override on the command line if needed.
PICO_SDK_PATH ?= $(MPY_DIR)/lib/pico-sdk
#PICO_SDK_PATH ?= /mnt/c/users/eeli/.pico-sdk/sdk/2.2.0

$(info PICO_SDK_PATH=$(PICO_SDK_PATH))

# Name of module
MOD = VL53L7CX

# Source files (.c or .py)
SRC = ../MPY_wrapper.cpp ../vl53l7cx_api.cpp ../vl53l7cx_platform.cpp

# armv7m with single precision float
ARCH = armv7emsp

# has no effect?
# BOARD = RPI_PICO2_W

# Include to get the rules for compiling and linking the module
#include $(MPY_DIR)/py/dynruntime.mk

# Added c++ support
include dynruntime-cpp.mk
