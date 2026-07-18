/**
 * Custom Micropython wrapper for VL53L7CX c++ API
 */

// Include MicroPython API.
#include "py/runtime.h"
#include "vl53l7cx_class.h"

// Internal state for a Python VL53L7CX object.
typedef struct
{
    mp_obj_base_t base;
    bool destroyed;
    VL53L7CX *dev = nullptr;
} mp_obj_VL53L7CX_t;

// constructor VL53L7CX(...).
static mp_obj_t VL53L7CX_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    (void)args;
    mp_arg_check_num(n_args, n_kw, 0, 0, false);

    mp_obj_VL53L7CX_t *self = m_new_obj(mp_obj_VL53L7CX_t);
    self->base.type = type;
    self->destroyed = false;
    // self->dev = new VL53L7CX(I2C(...))
    return MP_OBJ_FROM_PTR(self);
}

// VL53L7CX.test_print(message)
static mp_obj_t VL53L7CX_test_print(mp_obj_t self_in, mp_obj_t message)
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
static MP_DEFINE_CONST_FUN_OBJ_2(VL53L7CX_test_print_obj, VL53L7CX_test_print);

// VL53L7CX.destroy()
static mp_obj_t VL53L7CX_destroy(mp_obj_t self_in)
{
    mp_obj_VL53L7CX_t *self = (mp_obj_VL53L7CX_t *)MP_OBJ_TO_PTR(self_in);
    if (self->dev != nullptr)
        delete self->dev;
    self->destroyed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(VL53L7CX_destroy_obj, VL53L7CX_destroy);

static const mp_rom_map_elem_t VL53L7CX_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_test_print), MP_ROM_PTR(&VL53L7CX_test_print_obj)},
    {MP_ROM_QSTR(MP_QSTR_destroy), MP_ROM_PTR(&VL53L7CX_destroy_obj)},
};
static MP_DEFINE_CONST_DICT(VL53L7CX_locals_dict, VL53L7CX_locals_dict_table);

static const mp_obj_type_t VL53L7CX_type = {
    {&mp_type_type},
    .name = MP_QSTR_VL53L7CX,
    .make_new = VL53L7CX_make_new,
    .locals_dict = (mp_obj_dict_t *)&VL53L7CX_locals_dict,
};

static const mp_rom_map_elem_t VL53L7CX_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_VL53L7CX)},
    {MP_ROM_QSTR(MP_QSTR_VL53L7CX), MP_ROM_PTR(&VL53L7CX_type)},
};
static MP_DEFINE_CONST_DICT(VL53L7CX_module_globals, VL53L7CX_module_globals_table);

const mp_obj_module_t VL53L7CX_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&VL53L7CX_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_VL53L7CX, VL53L7CX_user_cmodule);
