/**
 ******************************************************************************
 * @file    vl53l7cx_platform.h
 * @author  STMicroelectronics
 * @version V1.0.0
 * @date    11 November 2021
 * @brief   Header file of the platform dependent structures.
 ******************************************************************************
 * @attention
 *
 * <h2><center>&copy; COPYRIGHT(c) 2021 STMicroelectronics</center></h2>
 *
 * Redistribution and use in source and binary forms, with or without modification,
 * are permitted provided that the following conditions are met:
 *   1. Redistributions of source code must retain the above copyright notice,
 *      this list of conditions and the following disclaimer.
 *   2. Redistributions in binary form must reproduce the above copyright notice,
 *      this list of conditions and the following disclaimer in the documentation
 *      and/or other materials provided with the distribution.
 *   3. Neither the name of STMicroelectronics nor the names of its contributors
 *      may be used to endorse or promote products derived from this software
 *      without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 ******************************************************************************
 */

#ifndef _VL53L7CX_PLATFORM_H_
#define _VL53L7CX_PLATFORM_H_
#pragma once

#include <stdint.h>
#include "vl53l7cx_platform_config.h"
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "hardware/gpio.h"

// Include MicroPython API
#include "py/runtime.h"

// What's the meaning of this value in Pico?
#define DEFAULT_I2C_BUFFER_LEN 32

/* Wrappers for Pico SDK */

typedef i2c_inst_t TwoWire;

// print to stdout
#define print(...) mp_printf(&mp_plat_print, __VA_ARGS__)

// print error message
#define perror(...)     \
    print("Error: ");   \
    print(__VA_ARGS__); \
    print("\n");

/**
 * @brief Init I2C with given block and pins
 * @return static i2c instance
 */
static TwoWire *I2C(int id, int SDA_gpio, int SCL_gpio)
{
    i2c_inst_t *i2c = (id == 1) ? i2c1 : i2c0;
    // I2C Initialisation. Using it at 400Khz.
    i2c_init(i2c, 400 * 1000);

    gpio_set_function(SDA_gpio, GPIO_FUNC_I2C);
    gpio_set_function(SCL_gpio, GPIO_FUNC_I2C);
    gpio_pull_up(SDA_gpio);
    gpio_pull_up(SCL_gpio);
    return i2c;
}

#if 0
/**
 * @brief Scan the standard 7-bit address range similar to MicroPython's i2c.scan()
 */
static std::vector<uint8_t> i2c_scan(int id, uint32_t timeout_us = 2000)
{
    std::vector<uint8_t> found;
    i2c_inst_t *i2c = (id == 1) ? i2c1 : i2c0;

    for (uint8_t addr = 0x08; addr <= 0x77; ++addr)
    {
        uint8_t rxdata;
        int ret = i2c_write_timeout_us(i2c, addr, &rxdata, 1, false, timeout_us);
        if (ret != PICO_ERROR_GENERIC && ret != PICO_ERROR_TIMEOUT)
        {
            found.push_back(addr);
        }
    }

    print("I2C devices found: [");
    for (size_t i = 0; i < found.size(); ++i)
    {
        print("0x%02X", found[i]);
        if (i + 1 < found.size())
            print(", ");
    }
    print("]\n");
    return found;
}
#endif

/**
 * @brief Structure VL53L7CX_Platform needs to be filled by the customer,
 * depending on his platform. At least, it contains the VL53L7CX I2C address.
 * Some additional fields can be added, as descriptors, or platform
 * dependencies. Anything added into this structure is visible into the platform
 * layer.
 */

typedef struct
{
    uint16_t address;

    TwoWire *dev_i2c;

    int lpn_pin;

    int i2c_rst_pin;

} VL53L7CX_Platform;

#endif // _VL53L7CX_PLATFORM_H_
