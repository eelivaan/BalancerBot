/**
 * Custom Micropython wrapper for VL53L7CX c++ API
 */

#include "module.h"

// VL53L7CX object methods
static MP_DEFINE_CONST_FUN_OBJ_2(VL53L7CX_test_print_obj, VL53L7CX_test_print);
static MP_DEFINE_CONST_FUN_OBJ_1(VL53L7CX_destroy_obj, VL53L7CX_destroy);
static MP_DEFINE_CONST_FUN_OBJ_3(VL53L7CX_configure_obj, VL53L7CX_configure);
static MP_DEFINE_CONST_FUN_OBJ_1(VL53L7CX_start_ranging_obj, VL53L7CX_start_ranging);
static MP_DEFINE_CONST_FUN_OBJ_1(VL53L7CX_stop_ranging_obj, VL53L7CX_stop_ranging);
static MP_DEFINE_CONST_FUN_OBJ_1(VL53L7CX_is_data_ready_obj, VL53L7CX_is_data_ready);
static MP_DEFINE_CONST_FUN_OBJ_1(VL53L7CX_get_ranging_data_obj, VL53L7CX_get_ranging_data);

// VL53L7CX object locals dict
static const mp_rom_map_elem_t VL53L7CX_locals_dict_table[] = {
    // VL53L7CX.test_print(message)
    {MP_ROM_QSTR(MP_QSTR_test_print), MP_ROM_PTR(&VL53L7CX_test_print_obj)},
    // VL53L7CX.destroy()
    {MP_ROM_QSTR(MP_QSTR_destroy), MP_ROM_PTR(&VL53L7CX_destroy_obj)},
    // VL53L7CX.configure(...)
    {MP_ROM_QSTR(MP_QSTR_configure), MP_ROM_PTR(&VL53L7CX_configure_obj)},
    // VL53L7CX.start_ranging()
    {MP_ROM_QSTR(MP_QSTR_start_ranging), MP_ROM_PTR(&VL53L7CX_start_ranging_obj)},
    // VL53L7CX.stop_ranging()
    {MP_ROM_QSTR(MP_QSTR_stop_ranging), MP_ROM_PTR(&VL53L7CX_stop_ranging_obj)},
    // VL53L7CX.is_data_ready()
    {MP_ROM_QSTR(MP_QSTR_is_data_ready), MP_ROM_PTR(&VL53L7CX_is_data_ready_obj)},
    // VL53L7CX.get_ranging_data()
    {MP_ROM_QSTR(MP_QSTR_get_ranging_data), MP_ROM_PTR(&VL53L7CX_get_ranging_data_obj)},
};
static MP_DEFINE_CONST_DICT(VL53L7CX_locals_dict, VL53L7CX_locals_dict_table);

// VL53L7CX class type
static MP_DEFINE_CONST_OBJ_TYPE(
    VL53L7CX_type,
    MP_QSTR_VL53L7CX,
    MP_TYPE_FLAG_NONE,
    make_new, VL53L7CX_make_new,
    print, VL53L7CX_print,
    locals_dict, &VL53L7CX_locals_dict);

// VL53L7CX module globals dict
static const mp_rom_map_elem_t VL53L7CX_module_globals_table[] = {
    // module name
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_VL53L7CX)},
    // VL53L7CX class type
    {MP_ROM_QSTR(MP_QSTR_VL53L7CX), MP_ROM_PTR(&VL53L7CX_type)},
};
static MP_DEFINE_CONST_DICT(VL53L7CX_module_globals, VL53L7CX_module_globals_table);

// VL53L7CX module type
const mp_obj_module_t VL53L7CX_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&VL53L7CX_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_VL53L7CX, VL53L7CX_user_cmodule);