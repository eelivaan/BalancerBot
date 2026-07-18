/**
 * Custom Micropython wrapper for VL53L7CX c++ API
 */

// Include the header file to get access to the MicroPython API
#include "py/dynruntime.h"
#include "vl53l7cx_class.h"

// This is the type (VL53L7CX)
mp_obj_full_type_t mp_type_VL53L7CX;

// This is the internal state of a VL53L7CX instance.
typedef struct
{
    mp_obj_base_t base;
    mp_int_t n;
} mp_obj_VL53L7CX_t;

// Custom Exception type
mp_obj_full_type_t mp_type_VL53L7CXError;

// Essentially VL53L7CX.__new__ (but also kind of __init__).
// Takes a single argument
static mp_obj_t VL53L7CX_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args_in)
{
    mp_arg_check_num(n_args, n_kw, 1, 1, false);

    mp_obj_VL53L7CX_t *o = mp_obj_malloc(mp_obj_VL53L7CX_t, type);
    o->n = mp_obj_get_int(args_in[0]);

    if (o->n < 0)
    {
        mp_raise_msg((mp_obj_type_t *)&mp_type_VL53L7CXError, "argument must be zero or above");
    }

    return MP_OBJ_FROM_PTR(o);
}

static mp_int_t factorial_helper(mp_int_t x)
{
    if (x == 0)
    {
        return 1;
    }
    return x * factorial_helper(x - 1);
}

// Implements VL53L7CX.calculate()
static mp_obj_t VL53L7CX_calculate(mp_obj_t self_in)
{
    mp_obj_VL53L7CX_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(factorial_helper(self->n));
}
static MP_DEFINE_CONST_FUN_OBJ_1(VL53L7CX_calculate_obj, VL53L7CX_calculate);

// Locals dict for the VL53L7CX type (will have a single method, calculate,
// added in mpy_init).
mp_map_elem_t VL53L7CX_locals_dict_table[1];
static MP_DEFINE_CONST_DICT(VL53L7CX_locals_dict, VL53L7CX_locals_dict_table);

// This is the entry point and is called when the module is imported
extern "C" mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args)
{
    // This must be first, it sets up the globals dict and other things
    MP_DYNRUNTIME_INIT_ENTRY

    // Initialise the type.
    mp_type_VL53L7CX.base.type = (void *)&mp_type_type;
    mp_type_VL53L7CX.flags = MP_TYPE_FLAG_NONE;
    mp_type_VL53L7CX.name = MP_QSTR_VL53L7CX;
    MP_OBJ_TYPE_SET_SLOT(&mp_type_VL53L7CX, make_new, VL53L7CX_make_new, 0);
    VL53L7CX_locals_dict_table[0] = (mp_map_elem_t){MP_OBJ_NEW_QSTR(MP_QSTR_calculate), MP_OBJ_FROM_PTR(&VL53L7CX_calculate_obj)};
    MP_OBJ_TYPE_SET_SLOT(&mp_type_VL53L7CX, locals_dict, (void *)&VL53L7CX_locals_dict, 1);

    // Make the VL53L7CX type available on the module.
    mp_store_global(MP_QSTR_VL53L7CX, MP_OBJ_FROM_PTR(&mp_type_VL53L7CX));

    // Initialise the exception type.
    mp_obj_exception_init(&mp_type_VL53L7CXError, MP_QSTR_VL53L7CXError, &mp_type_Exception);

    // Make the VL53L7CXError type available on the module.
    mp_store_global(MP_QSTR_VL53L7CXError, MP_OBJ_FROM_PTR(&mp_type_VL53L7CXError));

    // This must be last, it restores the globals dict
    MP_DYNRUNTIME_INIT_EXIT
}