import numpy as np
import matplotlib.pyplot as plt
from serial import Serial
from time import sleep
import json
from collections import deque

code = """
from robot import BalancerBot
from time import sleep_ms
import json
bot = BalancerBot()
bot.startIMU()
while 1:
	bot.updateIMU()
	print(json.dumps(bot.measure_accel_with_time()))
	print(json.dumps(bot.measure_gyro_with_time()))
	sleep_ms(100)
"""

def main() -> None:
	history = 1000
	at = deque(maxlen=history)
	ax = deque(maxlen=history)
	ay = deque(maxlen=history)
	az = deque(maxlen=history)

	gt = deque(maxlen=history)
	gx = deque(maxlen=history)
	gy = deque(maxlen=history)
	gz = deque(maxlen=history)

	fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

	# Top plot
	plotAx, = axes[0].plot([], [], label="x")
	plotAy, = axes[0].plot([], [], label="y")
	plotAz, = axes[0].plot([], [], label="z")
	axes[0].set_title("Accelerometer")
	axes[0].set_ylabel("Value")
	axes[0].grid(True, alpha=0.3)
	axes[0].legend(loc="upper right")

	# Bottom plot
	plotGx, = axes[1].plot([], [], label="x")
	plotGy, = axes[1].plot([], [], label="y")
	plotGz, = axes[1].plot([], [], label="z")
	axes[1].set_title("Gyroscope")
	axes[1].set_xlabel("Time")
	axes[1].set_ylabel("Value")
	axes[1].grid(True, alpha=0.3)
	axes[1].legend(loc="upper right")

	plt.tight_layout()
	plt.show(block=False)

	with Serial("COM9", 115200, timeout=2) as ser:
		print("COM9 opened")
		sleep(1)
		ser.write(b'\n')
		sleep(1)
		ser.write(b'\x03\n') # CTRL-C
		sleep(1)
		ser.write(b'\x02\n') # CTRL-B
		sleep(1)
		print(ser.read_all().decode(errors="ignore"))

		print("Writing code...")
		ser.write(code.encode() + b'\n')

		try:
			print("Running matplotlib event loop (close plot window to stop)...")
			while plt.fignum_exists(fig.number):
				if ser.in_waiting:
					msg = ser.read_all().decode(errors="ignore")
					it = iter(msg.split('\n'))
					try:
						if "True" in next(it):
							accel = json.loads(next(it))
							at.append(accel['t'])
							ax.append(accel['x'])
							ay.append(accel['y'])
							az.append(accel['z'])
							plotAx.set_data(np.array(at), np.array(ax))
							plotAy.set_data(np.array(at), np.array(ay))
							plotAz.set_data(np.array(at), np.array(az))
							axes[0].relim()
							axes[0].autoscale_view()

							gyro = json.loads(next(it))
							gt.append(gyro['t'])
							gx.append(gyro['x'])
							gy.append(gyro['y'])
							gz.append(gyro['z'])
							plotGx.set_data(np.array(gt), np.array(gx))
							plotGy.set_data(np.array(gt), np.array(gy))
							plotGz.set_data(np.array(gt), np.array(gz))
							axes[1].relim()
							axes[1].autoscale_view()
					except StopIteration:
						pass
				plt.pause(0.05)

		except Exception:
			ser.write(b'\x03\n') # CTRL-C
			raise
		
		ser.write(b'\x03\n') # CTRL-C


if __name__ == "__main__":
	main()
