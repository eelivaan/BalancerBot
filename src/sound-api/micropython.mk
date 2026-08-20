SOUND_MOD_DIR := $(USERMOD_DIR)

# Add our source files to the respective variables.
SRC_USERMOD += $(SOUND_MOD_DIR)/module.c
SRC_USERMOD_CXX += $(SOUND_MOD_DIR)/module_impl.cpp
SRC_USERMOD_CXX += $(SOUND_MOD_DIR)/SoundGenerator.cpp

# Add our module directory to the include path.
CFLAGS_USERMOD += -I$(SOUND_MOD_DIR)
CXXFLAGS_USERMOD += -I$(SOUND_MOD_DIR) -std=c++11 -Wno-error

# Add any necessary paths to library files.
# LDFLAGS_USERMOD += -Lpath/to/libs

# We use C++ features so have to link against the standard library.
LIBS_USERMOD += -lstdc++
