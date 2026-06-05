from machine import Pin, PWM
from utime import sleep_ms

led_builtin = Pin("LED", Pin.OUT)
led_builtin.on()

servo1_PWM = PWM(Pin("GP17"), freq=50)
servo2_PWM = PWM(Pin("GP16"), freq=50)

for i in range(50, 251, 10):
    print("Servo pulse width (ms):", i)
    servo1_PWM.duty_ns(int(i * 1000000 / 100))
    servo2_PWM.duty_ns(int(i * 1000000 / 100))
    sleep_ms(1000)

servo1_PWM.duty_ns(0)  # Stop sending pulses
servo2_PWM.duty_ns(0)  # Stop sending pulses
led_builtin.off()