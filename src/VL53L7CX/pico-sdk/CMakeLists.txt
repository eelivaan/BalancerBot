cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS OFF)

set(USERHOME /mnt/c/Users/eeli/)

set(picotoolVersion "2.2.0-a4")
set(PICO_SDK_PATH "${USERHOME}/.pico-sdk/sdk/2.2.0")
#set(PICO_TOOLCHAIN_PATH "${USERHOME}/.pico-sdk/toolchain/14_2_Rel1")

set(picotool_HINT "${USERHOME}/.pico-sdk/picotool/${picotoolVersion}/picotool")
if(EXISTS ${picotool_HINT})
        set(picotool_DIR ${picotool_HINT})
endif()

set(PICO_BOARD pico2_w CACHE STRING "Board type")

# initialize the SDK directly
include(pico_sdk_import.cmake)

project(my_project C CXX ASM)

# initialize the Raspberry Pi Pico SDK
pico_sdk_init()

#add_executable(my_project main.c)

# rest of your project
# Add the standard library to the build
#target_link_libraries(my_project pico_stdlib)

# Add the standard include files to the build
#target_include_directories(my_project PRIVATE ${CMAKE_CURRENT_LIST_DIR})