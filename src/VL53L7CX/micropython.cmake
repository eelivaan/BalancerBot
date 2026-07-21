# Create an INTERFACE library for our CPP module.
add_library(usermod_VL53L7CX INTERFACE)

# Add our source files to the library.
target_sources(usermod_VL53L7CX INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/module.c
    ${CMAKE_CURRENT_LIST_DIR}/module_impl.cpp
    ${CMAKE_CURRENT_LIST_DIR}/vl53l7cx_api.cpp
    ${CMAKE_CURRENT_LIST_DIR}/vl53l7cx_platform.cpp
)

# Add the current directory as an include directory.
target_include_directories(usermod_VL53L7CX INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_VL53L7CX)
