#include <math.h>

extern "C"
{
#include "pico/stdlib.h"
#include "hardware/pwm.h"
#include "hardware/irq.h"
#include "SoundGenerator.h"

    SoundGenerator_t SoundGenerator;

    void on_pwm_wrap()
    {
        // Clear the interrupt flag that brought us here
        pwm_clear_irq(SoundGenerator.PWM_slice_num);

        uint64_t t = to_us_since_boot(get_absolute_time());
        SoundGenerator.tick(t);
    }

    void SoundGenerator_t::init(uint gpio)
    {
        PWM_Pin = gpio;

        // Tell the pin that the PWM is in charge of its value.
        gpio_set_function(PWM_Pin, GPIO_FUNC_PWM);
        // Figure out which slice we just connected to the pin
        PWM_slice_num = pwm_gpio_to_slice_num(PWM_Pin);

        // Mask our slice's IRQ output into the PWM block's single interrupt line,
        // and register our interrupt handler
        pwm_clear_irq(PWM_slice_num);
        pwm_set_irq_enabled(PWM_slice_num, true);
        irq_set_exclusive_handler(PWM_DEFAULT_IRQ_NUM(), on_pwm_wrap);
        // irq off until sounds are actually played
        irq_set_enabled(PWM_DEFAULT_IRQ_NUM(), false);

        // Get some sensible defaults for the slice configuration. By default, the
        // counter is allowed to wrap over its maximum range (0 to 2**16-1)
        pwm_config config = pwm_get_default_config();
        // Set divider, reduces counter clock to sysclock/this value
        pwm_config_set_clkdiv(&config, 1.f);
        // approx 44.1 kHz sample rate with 150 MHz processor clocking
        pwm_config_set_wrap(&config, 3400);
        // Load the configuration into our PWM slice, and set it off until sounds are actually played.
        pwm_init(PWM_slice_num, &config, false);
    }

    void SoundGenerator_t::tick(uint64_t time_us)
    {
        if (!PWM_Pin)
            return;

        // play procedural sinewave while requested
        if (time_us < next_silence_us)
        {
            sinewave(time_us / 1e6);
        }
        else
        {
            pwm_set_gpio_level(PWM_Pin, 0u);
            if (time_us - next_silence_us > 5000000)
            {
                // disable irq and PWM after 5 seconds of inactivity
                irq_set_enabled(PWM_DEFAULT_IRQ_NUM(), false);
                pwm_set_enabled(PWM_slice_num, false);
            }
        }
    }

    void SoundGenerator_t::beep(float frequency, float duration)
    {
        // enable irq and PWM
        irq_set_enabled(PWM_DEFAULT_IRQ_NUM(), true);
        pwm_set_enabled(PWM_slice_num, true);

        wave_freq = frequency;
        next_silence_us = to_us_since_boot(get_absolute_time()) + (uint64_t)(duration * 1e6);
    }

    void SoundGenerator_t::sinewave(float time)
    {
        float value = 0.5 + 0.5 * sinf(2 * M_PI * wave_freq * time);
        // value *= (0.5 + 0.5 * sinf(2 * M_PI * 0.4 * t)); // Amplitude modulation at 0.4 Hz
        value *= volume;
        pwm_set_gpio_level(PWM_Pin, (uint16_t)(value * 65535));
    }
}