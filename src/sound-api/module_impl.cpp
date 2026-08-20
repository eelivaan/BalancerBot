
extern "C"
{
#include "module.h"
#include "SoundGenerator.h"

    typedef struct _mp_obj_Speaker_t
    {
        mp_obj_base_t base;
    } mp_obj_Speaker_t;

    void Speaker_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
    {
        mp_obj_Speaker_t *self = (mp_obj_Speaker_t *)MP_OBJ_TO_PTR(self_in);
        (void)self;
        mp_printf(print, "Speaker object with volume=%f)", SoundGenerator.volume);
    }

    mp_obj_t Speaker_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
    {
        mp_arg_check_num(n_args, n_kw, 1, 1, false);

        mp_obj_Speaker_t *self = mp_obj_malloc(mp_obj_Speaker_t, type);
        int gpio = mp_obj_get_int(args[0]);

        SoundGenerator.volume = 0.5;
        SoundGenerator.init((uint)gpio);

        return MP_OBJ_FROM_PTR(self);
    }

    mp_obj_t Speaker_volume(size_t n_args, const mp_obj_t *args)
    {
        mp_obj_Speaker_t *self = (mp_obj_Speaker_t *)MP_OBJ_TO_PTR(args[0]);
        (void)self;

        if (n_args == 1)
        {
            return mp_obj_new_float(SoundGenerator.volume);
        }

        float new_volume = mp_obj_get_float(args[1]);
        if (new_volume < 0.0f)
            new_volume = 0.0f;
        else if (new_volume > 1.0f)
            new_volume = 1.0f;

        SoundGenerator.volume = new_volume;
        return mp_obj_new_float(SoundGenerator.volume);
    }

    mp_obj_t Speaker_beep(mp_obj_t self_in, mp_obj_t frequency, mp_obj_t duration)
    {
        mp_obj_Speaker_t *self = (mp_obj_Speaker_t *)MP_OBJ_TO_PTR(self_in);
        (void)self;

        float freq = mp_obj_get_float(frequency);
        float dur = mp_obj_get_float(duration);
        SoundGenerator.beep(freq, dur);
        return mp_const_none;
    }
}