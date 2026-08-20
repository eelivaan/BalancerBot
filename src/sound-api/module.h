// Include MicroPython API
#include "py/runtime.h"

extern void Speaker_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
extern mp_obj_t Speaker_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
extern mp_obj_t Speaker_volume(size_t n_args, const mp_obj_t *args);
extern mp_obj_t Speaker_beep(mp_obj_t self_in, mp_obj_t frequency, mp_obj_t duration);

extern const mp_obj_type_t Speaker_type;
