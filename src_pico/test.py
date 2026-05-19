from machine import Pin, PWM, Timer
from utime import sleep_ms

led_builtin = Pin("LED", Pin.OUT)
led_builtin.on()

motorLA_PWM = PWM(Pin("GP19"), freq=1000)
motorLB_PWM = PWM(Pin("GP18"), freq=1000)

for i in range(255, 0, -30):
    print("Motor speed:", i)
    motorLA_PWM.duty_u16(i * 256)
    motorLB_PWM.duty_u16(0)
    sleep_ms(1500)

motorLA_PWM.duty_u16(0)
motorLB_PWM.duty_u16(0)

led_builtin.off()