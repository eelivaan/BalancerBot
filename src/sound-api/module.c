#include "module.h"

// Speaker object methods
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(Speaker_volume_obj, 1, 2, Speaker_volume);
static MP_DEFINE_CONST_FUN_OBJ_3(Speaker_beep_obj, Speaker_beep);

// Speaker object locals dict
static const mp_rom_map_elem_t Speaker_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_volume), MP_ROM_PTR(&Speaker_volume_obj)},
    {MP_ROM_QSTR(MP_QSTR_beep), MP_ROM_PTR(&Speaker_beep_obj)},
};
static MP_DEFINE_CONST_DICT(Speaker_locals_dict, Speaker_locals_dict_table);

// Speaker class type
MP_DEFINE_CONST_OBJ_TYPE(
    Speaker_type,
    MP_QSTR_Speaker,
    MP_TYPE_FLAG_NONE,
    make_new, Speaker_make_new,
    print, Speaker_print,
    locals_dict, &Speaker_locals_dict);

// sound module globals dict
static const mp_rom_map_elem_t sound_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_sound)},
    {MP_ROM_QSTR(MP_QSTR_Speaker), MP_ROM_PTR(&Speaker_type)},
};
static MP_DEFINE_CONST_DICT(sound_module_globals, sound_module_globals_table);

// sound module type
const mp_obj_module_t sound_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&sound_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_sound, sound_user_cmodule);
