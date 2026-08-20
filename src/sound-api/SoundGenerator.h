
class SoundGenerator_t
{
public:
    // Volume of the sound output 0-1
    float volume = 0.5;

    // Init PWM and other things necessary
    void init(uint gpio);

    void tick(uint64_t time_us);

    // Beep at given frequency for duration seconds
    void beep(float frequency, float duration);

    uint PWM_slice_num = 0;

private:
    // Pin to use for the speaker PWM signal
    uint PWM_Pin = 0;

    // Current sinewave frequency
    float wave_freq = 440.0;

    // Timestamp for the next silence
    uint64_t next_silence_us = 0;

    // Play sinewave at given frequency
    inline void sinewave(float time);
};

extern SoundGenerator_t SoundGenerator;
