/**
 ******************************************************************************
 * @file    vl53l7cx_platform.cpp
 * @author  STMicroelectronics
 * @version V1.0.0
 * @date    11 November 2021
 * @brief   Implementation of the platform dependent APIs.
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

extern "C"
{
#include "vl53l7cx_class.h"

#define TIMEOUT make_timeout_time_ms(2000)

    uint8_t VL53L7CX::RdByte(
        VL53L7CX_Platform *p_platform,
        uint16_t RegisterAddress,
        uint8_t *p_value)
    {
        uint8_t status = RdMulti(p_platform, RegisterAddress, p_value, 1);
        return status;
    }

    uint8_t VL53L7CX::WrByte(
        VL53L7CX_Platform *p_platform,
        uint16_t RegisterAddress,
        uint8_t value)
    {
        // Just use WrMulti but 1 byte
        uint8_t status = WrMulti(p_platform, RegisterAddress, &value, 1);
        return status;
    }

    uint8_t VL53L7CX::WrMulti(
        VL53L7CX_Platform *p_platform,
        uint16_t RegisterAddress,
        uint8_t *p_values,
        uint32_t size)
    {
        int status = 0;
        uint32_t i = 0;
        uint8_t buffer[2];
        const uint8_t addr = (uint8_t)((p_platform->address >> 1) & 0x7F);

#ifndef DEFAULT_I2C_BUFFER_LEN
        // Target register address for transfer
        buffer[0] = (uint8_t)(RegisterAddress >> 8);
        buffer[1] = (uint8_t)(RegisterAddress & 0xFF);
        status |= i2c_write_blocking_until(p_platform->dev_i2c, addr, buffer, 2, true, TIMEOUT) != 2;
        status |= i2c_write_blocking_until(p_platform->dev_i2c, addr, p_values, size, false, TIMEOUT) != size;
#else
        // chunked transaction
        while (i < size)
        {
            // If still more than DEFAULT_I2C_BUFFER_LEN bytes to go, DEFAULT_I2C_BUFFER_LEN,
            // else the remaining number of bytes
            size_t current_write_size = (size - i > DEFAULT_I2C_BUFFER_LEN ? DEFAULT_I2C_BUFFER_LEN : size - i);

            // Target register address for transfer
            buffer[0] = (uint8_t)((RegisterAddress + i) >> 8);
            buffer[1] = (uint8_t)((RegisterAddress + i) & 0xFF);
            status |= i2c_write_burst_blocking(p_platform->dev_i2c, addr, buffer, 2) != 2;
            status |= i2c_write_blocking_until(p_platform->dev_i2c, addr, p_values + i, current_write_size, false, TIMEOUT) != (int)current_write_size;
            if (status != 0)
                break;
            i += current_write_size;
        }
#endif

        if (status != 0)
            perror("VL53L7CX::WrMulti failed %d\n", status);
        return status;
    }

    uint8_t VL53L7CX::RdMulti(
        VL53L7CX_Platform *p_platform,
        uint16_t RegisterAddress,
        uint8_t *p_values,
        uint32_t size)
    {
        int status = 0;
        uint8_t buffer[2];
        const uint8_t addr = (uint8_t)((p_platform->address >> 1) & 0x7F);

        // Target register address for transfer
        buffer[0] = (uint8_t)(RegisterAddress >> 8);
        buffer[1] = (uint8_t)(RegisterAddress & 0xFF);
        status |= i2c_write_blocking_until(p_platform->dev_i2c, addr, buffer, 2, true, TIMEOUT) != 2;

        if (status == 0)
            status |= i2c_read_blocking_until(p_platform->dev_i2c, addr, p_values, size, false, TIMEOUT) != (int)size;

        if (status != 0)
            perror("VL53L7CX::RdMulti failed %d/%d\n", status, size);
        return status;
    }

    void VL53L7CX::SwapBuffer(
        uint8_t *buffer,
        uint16_t size)
    {
        uint32_t i, tmp;

        /* Example of possible implementation using <string.h> */
        for (i = 0; i < size; i = i + 4)
        {
            tmp = (buffer[i] << 24) | (buffer[i + 1] << 16) | (buffer[i + 2] << 8) | (buffer[i + 3]);

            memcpy(&(buffer[i]), &tmp, 4);
        }
    }

    uint8_t VL53L7CX::WaitMs(
        VL53L7CX_Platform *p_platform,
        uint32_t TimeMs)
    {
        (void)p_platform;
        sleep_ms(TimeMs);

        return 0;
    }
}