/**
 * Custom Micropython wrapper for VL53L7CX c++ API
 */

#include "module.h"

// VL53L7CX object methods
static MP_DEFINE_CONST_FUN_OBJ_2(VL53L7CX_test_print_obj, VL53L7CX_test_print);
static MP_DEFINE_CONST_FUN_OBJ_1(VL53L7CX_destroy_obj, VL53L7CX_destroy);

// VL53L7CX object locals dict
static const mp_rom_map_elem_t VL53L7CX_locals_dict_table[] = {
    // VL53L7CX.test_print(message)
    {MP_ROM_QSTR(MP_QSTR_test_print), MP_ROM_PTR(&VL53L7CX_test_print_obj)},
    // VL53L7CX.destroy()
    {MP_ROM_QSTR(MP_QSTR_destroy), MP_ROM_PTR(&VL53L7CX_destroy_obj)},
};
static MP_DEFINE_CONST_DICT(VL53L7CX_locals_dict, VL53L7CX_locals_dict_table);

// VL53L7CX class type
static MP_DEFINE_CONST_OBJ_TYPE(
    VL53L7CX_type,
    MP_QSTR_VL53L7CX,
    MP_TYPE_FLAG_NONE,
    make_new, VL53L7CX_make_new,
    locals_dict, &VL53L7CX_locals_dict);

// VL53L7CX module globals dict
static const mp_rom_map_elem_t VL53L7CX_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_VL53L7CX)},
    {MP_ROM_QSTR(MP_QSTR_VL53L7CX), MP_ROM_PTR(&VL53L7CX_type)},
};
static MP_DEFINE_CONST_DICT(VL53L7CX_module_globals, VL53L7CX_module_globals_table);

// VL53L7CX module type
const mp_obj_module_t VL53L7CX_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&VL53L7CX_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_VL53L7CX, VL53L7CX_user_cmodule);