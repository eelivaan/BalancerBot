/**
 * Custom Micropython wrapper for VL53L7CX c++ API
 * Declaration has to be compatible with C so everything goes in extern "C" scope.
 */

extern "C"
{
#include "module.h"
// Include VL53L7CX API
#include "vl53l7cx_class.h"

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

    // Internal state for a Python VL53L7CX object.
    typedef struct
    {
        mp_obj_base_t base;
        bool destroyed;
        VL53L7CX dev;
    } mp_obj_VL53L7CX_t;

    // constructor VL53L7CX(...).
    mp_obj_t VL53L7CX_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
    {
        (void)args;
        mp_arg_check_num(n_args, n_kw, 0, 0, false);

        mp_obj_VL53L7CX_t *self = mp_obj_malloc(mp_obj_VL53L7CX_t, type);
        self->destroyed = false;
        self->dev.configure(I2C(0, 20, 21), 19);

        return MP_OBJ_FROM_PTR(self);
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
        self->destroyed = true;
        return mp_const_none;
    }
}