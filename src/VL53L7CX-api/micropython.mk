VL53L7CX_MOD_DIR := $(USERMOD_DIR)

# Add our source files to the respective variables.
SRC_USERMOD += $(VL53L7CX_MOD_DIR)/module.c
SRC_USERMOD_CXX += $(VL53L7CX_MOD_DIR)/module_impl.cpp
SRC_USERMOD_CXX += $(VL53L7CX_MOD_DIR)/vl53l7cx_api.cpp
SRC_USERMOD_CXX += $(VL53L7CX_MOD_DIR)/vl53l7cx_platform.cpp

# Add our module directory to the include path.
CFLAGS_USERMOD += -I$(VL53L7CX_MOD_DIR)
CXXFLAGS_USERMOD += -I$(VL53L7CX_MOD_DIR) -std=c++11 -Wno-error

# Add any necessary paths to library files.
# LDFLAGS_USERMOD += -Lpath/to/libs

# We use C++ features so have to link against the standard library.
LIBS_USERMOD += -lstdc++
