// Include MicroPython API
#include "py/runtime.h"

// VL53L7CX object internals
extern mp_obj_t VL53L7CX_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
extern void VL53L7CX_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);

// VL53L7CX object methods
extern mp_obj_t VL53L7CX_test_print(mp_obj_t self_in, mp_obj_t message);
extern mp_obj_t VL53L7CX_destroy(mp_obj_t self_in);
extern mp_obj_t VL53L7CX_configure(mp_obj_t self_in, mp_obj_t resolution, mp_obj_t ranging_freq);
extern mp_obj_t VL53L7CX_start_ranging(mp_obj_t self_in);
extern mp_obj_t VL53L7CX_stop_ranging(mp_obj_t self_in);
extern mp_obj_t VL53L7CX_is_data_ready(mp_obj_t self_in);
extern mp_obj_t VL53L7CX_get_ranging_data(mp_obj_t self_in);
