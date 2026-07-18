cmake_minimum_required(VERSION 3.13)

# Keep existing user-home based SDK defaults.
if(WIN32)
        set(USERHOME "c:/users/eeli")
        set(picotoolVersion "2.2.0-a4")
        set(toolchainVersion "14_2_Rel1")
        set(MPY_DIR "${USERHOME}/documents/robotics/micropython-v1.28.0" CACHE PATH "Path to MicroPython source tree")
        # User-configurable paths (cached for easy override).
        set(PICO_SDK_PATH "${USERHOME}/.pico-sdk/sdk/2.2.0" CACHE PATH "Path to Pico SDK")
        set(PICO_TOOLCHAIN_PATH "${USERHOME}/.pico-sdk/toolchain/${toolchainVersion}")
        set(picotool_HINT "${USERHOME}/.pico-sdk/picotool/${picotoolVersion}/picotool")
else()
        set(USERHOME "/home/eeli")
        set(MPY_DIR "${USERHOME}/pico/micropython" CACHE PATH "Path to MicroPython source tree")
        set(PICO_SDK_PATH "${MPY_DIR}/lib/pico-sdk" CACHE PATH "Path to Pico SDK")
endif()

if(EXISTS ${picotool_HINT})
        set(picotool_DIR ${picotool_HINT})
endif()

set(PICO_BOARD pico2_w CACHE STRING "Board type")

# Module settings from the Makefile.
set(MOD VL53L7CX)
set(ARCH armv7emsp)  # armv7m with single precision float
option(LINK_RUNTIME "Link runtime libs into native mpy (dynruntime-cpp.mk LINK_RUNTIME)" OFF)
set(MPY_EXTERN_SYM_FILE "" CACHE FILEPATH "Path to extern symbol file for mpy_ld (--externs)")
set(ARCH_FLAGS "" CACHE STRING "Optional architecture flags for mpy_ld (--arch-flags)")

message(STATUS "PICO_SDK_PATH = ${PICO_SDK_PATH}")
message(STATUS "MPY_DIR = ${MPY_DIR}")
message(STATUS "MPY_EXTERN_SYM_FILE = ${MPY_EXTERN_SYM_FILE}")

# Must be included before project() so the Pico SDK toolchain file is applied
# and CMake selects arm-none-eabi-gcc/g++ during the project() call.
include(pico_sdk_import.cmake)

project(VL53L7CX_dynruntime C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS OFF)

# initialize the Raspberry Pi Pico SDK
pico_sdk_init()

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(MPY_CROSS "${MPY_DIR}/mpy-cross/build/mpy-cross")
set(MPY_TOOL "${MPY_DIR}/tools/mpy-tool.py")
set(MPY_LD "${MPY_DIR}/tools/mpy_ld.py")

set(MPY_LD_LINK_ARGS)
if(LINK_RUNTIME)
        execute_process(
                COMMAND "${CMAKE_C_COMPILER}" -mthumb -mcpu=cortex-m33 --print-libgcc-file-name
                OUTPUT_VARIABLE LIBGCC_PATH
                OUTPUT_STRIP_TRAILING_WHITESPACE
        )
        execute_process(
                COMMAND "${CMAKE_C_COMPILER}" -mthumb -mcpu=cortex-m33 --print-file-name=libm.a
                OUTPUT_VARIABLE LIBM_PATH
                OUTPUT_STRIP_TRAILING_WHITESPACE
        )
        if(LIBGCC_PATH)
                list(APPEND MPY_LD_LINK_ARGS -l "${LIBGCC_PATH}")
        endif()
        if(LIBM_PATH)
                list(APPEND MPY_LD_LINK_ARGS -l "${LIBM_PATH}")
        endif()
endif()

if(MPY_EXTERN_SYM_FILE)
        get_filename_component(MPY_EXTERN_SYM_FILE_REAL "${MPY_EXTERN_SYM_FILE}" REALPATH BASE_DIR "${CMAKE_CURRENT_LIST_DIR}")
        list(APPEND MPY_LD_LINK_ARGS --externs "${MPY_EXTERN_SYM_FILE_REAL}")
endif()

if(ARCH_FLAGS)
        list(APPEND MPY_LD_LINK_ARGS --arch-flags "${ARCH_FLAGS}")
endif()

set(MODULE_SOURCES
        "${CMAKE_CURRENT_LIST_DIR}/dynruntime-module.cpp"
        "${CMAKE_CURRENT_LIST_DIR}/../vl53l7cx_api.cpp"
        "${CMAKE_CURRENT_LIST_DIR}/../vl53l7cx_platform.cpp"
)

# Optional Python module sources in this folder (*.py).
file(GLOB MODULE_PY_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_LIST_DIR}/*.py")

set(BUILD_DIR "${CMAKE_CURRENT_BINARY_DIR}/build")
set(CONFIG_H "${BUILD_DIR}/${MOD}.config.h")
set(NATIVE_MPY "${BUILD_DIR}/${MOD}.native.mpy")
set(FINAL_MPY "${CMAKE_CURRENT_BINARY_DIR}/${MOD}.mpy")

file(MAKE_DIRECTORY "${BUILD_DIR}")

# Generate dynruntime config header (equivalent to mpy_ld --preprocess).
add_custom_command(
        OUTPUT "${CONFIG_H}"
        COMMAND "${Python3_EXECUTABLE}" "${MPY_LD}" --arch "${ARCH}" --preprocess -o "${CONFIG_H}" ${MODULE_SOURCES}
        DEPENDS ${MODULE_SOURCES} "${MPY_LD}"
        WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}"
        COMMAND_EXPAND_LISTS
        VERBATIM
)
add_custom_target(${MOD}_config DEPENDS "${CONFIG_H}")

add_library(${MOD}_obj OBJECT ${MODULE_SOURCES})
add_dependencies(${MOD}_obj ${MOD}_config)

target_include_directories(${MOD}_obj PRIVATE
        "${CMAKE_CURRENT_LIST_DIR}"
        "${BUILD_DIR}"
)
target_include_directories(${MOD}_obj SYSTEM PRIVATE
        "${MPY_DIR}"
)

# Match dynruntime-cpp.mk flags.
target_compile_options(${MOD}_obj PRIVATE
        $<$<COMPILE_LANGUAGE:C>:
                -std=c11
                -Os
                -Wall
                -Werror
                -DNDEBUG
                -fpic
                -fno-common
                -mthumb
                -mcpu=cortex-m33
                -U_FORTIFY_SOURCE
        >
        $<$<COMPILE_LANGUAGE:CXX>:
                -std=c++17
                -Os
                -Wall
                -DNDEBUG
                -fpermissive
                -fno-exceptions
                -fno-rtti
                -fno-unwind-tables
                -fno-asynchronous-unwind-tables
                -fno-threadsafe-statics
                -fno-use-cxa-atexit
                -fpic
                -fno-common
                -mthumb
                -mcpu=cortex-m33
                -U_FORTIFY_SOURCE
        >
)

target_compile_definitions(${MOD}_obj PRIVATE
        NO_QSTR
        MICROPY_ENABLE_DYNRUNTIME
        MICROPY_FLOAT_IMPL=MICROPY_FLOAT_IMPL_FLOAT
        "MP_CONFIGFILE=<${CONFIG_H}>"
)


# Collect hardware library files to pass to mpy_ld as -l args.
set(MPY_LD_HW_LIB_ARGS)
set(MPY_LD_HW_DEPENDS)

# Pull Pico SDK include paths/defines into dynruntime compilation.
if(TARGET pico_stdlib)
#        target_link_libraries(${MOD}_obj PRIVATE pico_stdlib)
endif()
target_include_directories(${MOD}_obj PRIVATE
        $<TARGET_PROPERTY:pico_stdlib,INTERFACE_INCLUDE_DIRECTORIES>
        $<TARGET_PROPERTY:hardware_gpio,INTERFACE_INCLUDE_DIRECTORIES>
        $<TARGET_PROPERTY:hardware_i2c,INTERFACE_INCLUDE_DIRECTORIES>)

target_compile_definitions(${MOD}_obj PRIVATE
        $<TARGET_PROPERTY:pico_stdlib,INTERFACE_COMPILE_DEFINITIONS>
        $<TARGET_PROPERTY:hardware_gpio,INTERFACE_COMPILE_DEFINITIONS>
        $<TARGET_PROPERTY:hardware_i2c,INTERFACE_COMPILE_DEFINITIONS>)


# Compile any optional .py sources to .mpy.
set(PY_MPY_FILES)
foreach(py_src IN LISTS MODULE_PY_SOURCES)
        get_filename_component(py_name "${py_src}" NAME_WE)
        set(py_mpy "${BUILD_DIR}/${py_name}.mpy")

        add_custom_command(
                OUTPUT "${py_mpy}"
                COMMAND "${MPY_CROSS}" -march="${ARCH}" -o "${py_mpy}" "${py_src}"
                DEPENDS "${py_src}" "${MPY_CROSS}"
                WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}"
                VERBATIM
        )
        list(APPEND PY_MPY_FILES "${py_mpy}")
endforeach()

# Link native module (.native.mpy).
add_custom_command(
        OUTPUT "${NATIVE_MPY}"
        COMMAND "${Python3_EXECUTABLE}" "${MPY_LD}" --arch "${ARCH}" --qstrs "${CONFIG_H}" ${MPY_LD_LINK_ARGS} ${MPY_LD_HW_LIB_ARGS} -o "${NATIVE_MPY}" $<TARGET_OBJECTS:${MOD}_obj>
        DEPENDS ${MOD}_obj ${MPY_LD_HW_DEPENDS} "${CONFIG_H}" "${MPY_LD}"
        WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}"
        COMMAND_EXPAND_LISTS
        VERBATIM
)

# Merge final module (.mpy).
if(PY_MPY_FILES)
        add_custom_command(
                OUTPUT "${FINAL_MPY}"
                COMMAND "${Python3_EXECUTABLE}" "${MPY_TOOL}" --merge -o "${FINAL_MPY}" "${NATIVE_MPY}" ${PY_MPY_FILES}
                DEPENDS "${NATIVE_MPY}" ${PY_MPY_FILES} "${MPY_TOOL}"
                WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}"
                VERBATIM
        )
else()
        add_custom_command(
                OUTPUT "${FINAL_MPY}"
                COMMAND "${Python3_EXECUTABLE}" "${MPY_TOOL}" --merge -o "${FINAL_MPY}" "${NATIVE_MPY}"
                DEPENDS "${NATIVE_MPY}" "${MPY_TOOL}"
                WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}"
                VERBATIM
        )
endif()

add_custom_target(${MOD}_mpy ALL DEPENDS "${FINAL_MPY}")
