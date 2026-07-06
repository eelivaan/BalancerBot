from machine import I2C, Pin
import time

from VL53L7CX import VL53L7CX

# Adjust these pins/bus if wiring is different.
I2C_BUS = 0
I2C_SCL_PIN = "GP21"
I2C_SDA_PIN = "GP20"
I2C_FREQ = 400000


def print_8x8_grid(distance_mm):
    if len(distance_mm) < 64:
        print("Distance payload is too short:", len(distance_mm))
        return

    print("8x8 distance map (mm):")
    for row in range(8):
        base = row * 8
        line = " ".join("{:4d}".format(distance_mm[base + col]) for col in range(8))
        print(line)


def wait_for_frame(sensor, timeout_ms=2000):
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        status, ready = sensor.vl53l7cx_check_data_ready()
        if status != 0:
            print("check_data_ready status:", status)
        if ready:
            return True
        time.sleep_ms(50)
    return False


i2c = I2C(I2C_BUS, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=I2C_FREQ)

print("I2C scan:", [hex(x) for x in i2c.scan()])
#raise KeyboardInterrupt("Stop here to check I2C scan results before continuing.")

sensor = VL53L7CX(i2c, address=0x29)

if not sensor.vl53l7cx_is_alive():
    raise RuntimeError("VL53L7CX is not responding with expected ID")

status = sensor.init_sensor()
print("init_sensor status:", status)
if status != VL53L7CX.VL53L7CX_STATUS_OK:
    raise RuntimeError("init_sensor failed")

status = sensor.vl53l7cx_set_resolution(VL53L7CX.VL53L7CX_RESOLUTION_8X8)
print("set_resolution(8x8) status:", status)
if status != VL53L7CX.VL53L7CX_STATUS_OK:
    raise RuntimeError("set_resolution failed")

status = sensor.vl53l7cx_start_ranging()
print("start_ranging status:", status)
if status != VL53L7CX.VL53L7CX_STATUS_OK:
    raise RuntimeError("start_ranging failed")

try:
    # Print a few frames for quick functional verification.
    for frame in range(1):
        if 0:
            status, ready, raw = sensor.vl53l7cx_debug_poll_data_ready(max_polls=120, delay_ms=20)
            print("final:", status, ready, raw)

        elif not wait_for_frame(sensor):
            print("Timed out waiting for frame", frame)
            #continue

        status, results = sensor.vl53l7cx_get_ranging_data()
        print("frame", frame, "get_ranging_data status:", status)
        print("results:", results)
        if status != VL53L7CX.VL53L7CX_STATUS_OK or not results:
            continue

        print_8x8_grid(results.get("distance_mm", []))
        print("-")
        time.sleep_ms(100)
finally:
    stop_status = sensor.vl53l7cx_stop_ranging()
    print("stop_ranging status:", stop_status)
