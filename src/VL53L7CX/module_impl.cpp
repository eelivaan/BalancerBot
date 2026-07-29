/**
 * Custom Micropython wrapper for VL53L7CX c++ API
 * Declaration has to be compatible with C so everything goes in extern "C" scope.
 */

#include <stdio.h>

extern "C"
{
#include "module.h"
#include "extmod/modmachine.h" // machine_i2c_type
#include "vl53l7cx_class.h"    // Include VL53L7CX API

// Raise python RuntimeError with printf style parameters
#define raise_RuntimeError(...)                                  \
    {                                                            \
        char msg[100];                                           \
        snprintf(msg, 99, __VA_ARGS__);                          \
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT(msg)); \
    }

// Compare micropython string object to a constant
#define equals_const(string_obj, constant) (mp_obj_str_get_qstr(string_obj) == MP_QSTR_##constant)

// Don't know why standard headers don't have this
#define clamp(x, low, high) (x < low ? low : (x > high ? high : x))

    // Mirror RP2 machine_i2c_obj_t layout for extracting configured bus and pins.
    typedef struct
    {
        mp_obj_base_t base;
        i2c_inst_t *const i2c_inst;
        uint8_t i2c_id;
        uint8_t scl;
        uint8_t sda;
        uint32_t freq;
        uint32_t timeout;
    } rp2_machine_i2c_obj_t;

    // Internal state for a Python VL53L7CX object.
    typedef struct
    {
        mp_obj_base_t base;
        bool destroyed;
        bool is_ranging;
        VL53L7CX dev;
    } mp_obj_VL53L7CX_t;

    /**
     * Constructor VL53L7CX(i2c: machine.I2C, lpn_pin: Int, i2c_rst_pin: Int = -1)
     * n_args: number of positional arguments
     * n_kw: number of keyword arguments
     * args: array of positional arguments
     */
    mp_obj_t VL53L7CX_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
    {
        // check arguments
        mp_arg_check_num(n_args, n_kw, 2, 3, false);

        if (!mp_obj_is_type(args[0], &machine_i2c_type))
        {
            mp_raise_TypeError(MP_ERROR_TEXT("VL53L7CX() expected machine.I2C"));
        }

        // initialize VL53L7CX python object
        mp_obj_VL53L7CX_t *self = mp_obj_malloc(mp_obj_VL53L7CX_t, type);
        self->destroyed = false;
        self->is_ranging = false;

        // read arguments
        rp2_machine_i2c_obj_t *i2c = (rp2_machine_i2c_obj_t *)MP_OBJ_TO_PTR(args[0]);
        // int i2c_id = 0;
        // int i2c_sda = 20;
        // int i2c_scl = 21;
        int LPN_PIN = mp_obj_get_int(args[1]);
        int I2C_RST_PIN = (n_args > 2) ? mp_obj_get_int(args[2]) : -1;

        print("VL53L7CX init with i2c_inst=%d, SDA=%d, SCL=%d, LPN=%d, I2C_RST=%d\n",
              i2c->i2c_id, i2c->sda, i2c->scl, LPN_PIN, I2C_RST_PIN);

        // initialize the sensor
        int r = VL53L7CX_STATUS_OK;
        // self->dev.reconstruct(myI2C(i2c_id, i2c_sda, i2c_scl), LPN_PIN, I2C_RST_PIN);
        self->dev.reconstruct((i2c->i2c_id == 1 ? i2c1 : i2c0), LPN_PIN, I2C_RST_PIN);

        r = self->dev.begin();
        if (r != VL53L7CX_STATUS_OK)
            raise_RuntimeError("VL53L7CX->begin() failed with status %d", r);

        // Reset the sensor by toggling the LPN pin
        self->dev.vl53l7cx_off();
        self->dev.vl53l7cx_on();

        uint8_t isAlive = 0;
        r = self->dev.vl53l7cx_is_alive(&isAlive);
        if (isAlive && r == VL53L7CX_STATUS_OK)
            print("Sensor alive\n");
        else
            perror("Error: sensor not alive\n");

        // Init VL53L7CX sensor
        r = self->dev.vl53l7cx_init();
        if (r != VL53L7CX_STATUS_OK)
            raise_RuntimeError("VL53L7CX->vl53l7cx_init() failed with status %d", r);

        // r = self->dev.init_sensor();
        //  print("VL53L7CX->init_sensor(): %d\n", r);
        //    if (r != VL53L7CX_STATUS_OK)
        //        raise_RuntimeError("VL53L7CX->init_sensor() failed with status %d", r);

        r = self->dev.vl53l7cx_set_resolution(VL53L7CX_RESOLUTION_8X8);
        r = self->dev.vl53l7cx_set_ranging_frequency_hz(10);

        return MP_OBJ_FROM_PTR(self);
    }

    // VL53L7CX object to str
    void VL53L7CX_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
    {
        mp_obj_VL53L7CX_t *self = (mp_obj_VL53L7CX_t *)MP_OBJ_TO_PTR(self_in);
        uint8_t resolution, frequency;
        self->dev.vl53l7cx_get_resolution(&resolution);
        self->dev.vl53l7cx_get_ranging_frequency_hz(&frequency);
        mp_printf(print, "VL53L7CX Time-of-flight sensor: ranging: %s, res: %s, freq: %u Hz",
                  (self->is_ranging) ? "True" : "False",
                  (resolution == VL53L7CX_RESOLUTION_8X8) ? "8x8" : "4x4",
                  frequency);
    }

    // VL53L7CX.test_print(message)
    mp_obj_t VL53L7CX_test_print(mp_obj_t self_in, mp_obj_t message)
    {
        mp_obj_VL53L7CX_t *self = (mp_obj_VL53L7CX_t *)MP_OBJ_TO_PTR(self_in);
        if (self->destroyed)
        {
            mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("VL53L7CX object is destroyed"));
        }

        mp_printf(&mp_plat_print, "VL53L7CX: ");
        mp_obj_print_helper(&mp_plat_print, message, PRINT_STR);
        mp_printf(&mp_plat_print, "\n");
        return mp_const_none;
    }

    // VL53L7CX.destroy()
    mp_obj_t VL53L7CX_destroy(mp_obj_t self_in)
    {
        mp_obj_VL53L7CX_t *self = (mp_obj_VL53L7CX_t *)MP_OBJ_TO_PTR(self_in);
        if (self->is_ranging)
            self->dev.vl53l7cx_stop_ranging();
        // Free any dynamic allocations here
        self->destroyed = true;
        self->is_ranging = false;
        return mp_const_none;
    }

    /**
     * VL53L7CX.configure(resolution: str, ranging_freq: int) -> int
     * @param resolution : "8x8" or "4x4"
     * @param ranging_freq : The ranging frequency in Hz
     * - For 4x4, min and max allowed values are : [1;60]
     * - For 8x8, min and max allowed values are : [1;15]
     * @returns Status of the operation: 0 when succesful
     */
    mp_obj_t VL53L7CX_configure(mp_obj_t self_in, mp_obj_t resolution, mp_obj_t ranging_freq)
    {
        mp_obj_VL53L7CX_t *self = (mp_obj_VL53L7CX_t *)MP_OBJ_TO_PTR(self_in);
        uint8_t r = VL53L7CX_STATUS_OK;

        const uint8_t res = equals_const(resolution, 4x4) ? VL53L7CX_RESOLUTION_4X4 : VL53L7CX_RESOLUTION_8X8;
        r |= self->dev.vl53l7cx_set_resolution(res);

        uint8_t freq = (uint8_t)mp_obj_get_int(ranging_freq);
        freq = (res == VL53L7CX_RESOLUTION_4X4) ? clamp(freq, 1, 60) : clamp(freq, 1, 15);
        r |= self->dev.vl53l7cx_set_ranging_frequency_hz(freq);

        return mp_obj_new_int(r);
    }

    /**
     * VL53L7CX.start_ranging() -> int
     * @returns Status of the operation: 0 when succesful
     */
    mp_obj_t VL53L7CX_start_ranging(mp_obj_t self_in)
    {
        mp_obj_VL53L7CX_t *self = (mp_obj_VL53L7CX_t *)MP_OBJ_TO_PTR(self_in);
        uint8_t r = VL53L7CX_STATUS_OK;
        if (!self->is_ranging)
        {
            r = self->dev.vl53l7cx_start_ranging();
            if (r == VL53L7CX_STATUS_OK)
                self->is_ranging = true;
            else
                perror("vl53l7cx->start_ranging() status %u", r);
        }
        return mp_obj_new_int(r);
    }

    /**
     * VL53L7CX.stop_ranging() -> int
     * @returns Status of the operation: 0 when succesful
     */
    mp_obj_t VL53L7CX_stop_ranging(mp_obj_t self_in)
    {
        mp_obj_VL53L7CX_t *self = (mp_obj_VL53L7CX_t *)MP_OBJ_TO_PTR(self_in);
        uint8_t r = VL53L7CX_STATUS_OK;
        if (self->is_ranging)
        {
            r = self->dev.vl53l7cx_stop_ranging();
            if (r == VL53L7CX_STATUS_OK)
                self->is_ranging = false;
            else
                perror("vl53l7cx->stop_ranging() status %u", r);
        }
        return mp_obj_new_int(r);
    }

    /**
     * VL53L7CX.is_data_ready() -> bool
     * @returns True if ranging data is ready to be read
     */
    mp_obj_t VL53L7CX_is_data_ready(mp_obj_t self_in)
    {
        mp_obj_VL53L7CX_t *self = (mp_obj_VL53L7CX_t *)MP_OBJ_TO_PTR(self_in);
        uint8_t isReady = 0;
        uint8_t status = self->dev.vl53l7cx_check_data_ready(&isReady);
        if (status != VL53L7CX_STATUS_OK)
            perror("vl53l7cx->check_data_ready() status %u", status);
        return mp_obj_new_bool(isReady);
    }

    /**
     * VL53L7CX.get_ranging_data() -> list[Int|None]
     * @returns A list of distance measurements in mm or None on failure
     */
    mp_obj_t VL53L7CX_get_ranging_data(mp_obj_t self_in)
    {
        mp_obj_VL53L7CX_t *self = (mp_obj_VL53L7CX_t *)MP_OBJ_TO_PTR(self_in);
        if (self->is_ranging)
        {
            VL53L7CX_ResultsData results;
            uint8_t status = self->dev.vl53l7cx_get_ranging_data(&results);
            if (status == VL53L7CX_STATUS_OK)
            {
                mp_obj_t distance_array[VL53L7CX_RESOLUTION_8X8];
                uint8_t num_zones;
                status = self->dev.vl53l7cx_get_resolution(&num_zones);
                if (status != VL53L7CX_STATUS_OK)
                {
                    perror("vl53l7cx->get_resolution() status %u", status);
                    num_zones = VL53L7CX_RESOLUTION_8X8; // fallback to 8x8
                }
                // fill array of int objects with distance measurements or None if no target detected
                for (size_t i = 0; i < num_zones; i++)
                {
                    if (results.nb_target_detected[i] > 0)
                        distance_array[i] = mp_obj_new_int(results.distance_mm[i]);
                    else
                        distance_array[i] = mp_const_none;
                }
                return mp_obj_new_list(num_zones, distance_array);
            }
            else
            {
                perror("vl53l7cx->get_ranging_data() status %u", status);
            }
        }
        return mp_const_none;
    }
}