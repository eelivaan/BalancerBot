import numpy as np
import matplotlib.pyplot as plt
from serial import Serial
from time import sleep
import json, math
from collections import deque
from control import PIDController, sign

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

class Plotter:
	history_N = 400

	def addTimeSeries(self, key, axis):
		for x in 'txyz':
			setattr(self, f'{key}{x}', deque(maxlen=Plotter.history_N))
		for x in 'xyz':
			setattr(self, f'plot{key}{x}', axis.plot([], [], label=x))

	def addFrame(self, key, frameobj: dict):
		timeData = getattr(self, f'{key}t')
		timeData.append(frameobj['t'])
		for x in 'xyz':
			data = getattr(self, f'{key}{x}')
			data.append(frameobj[x])
			getattr(self, f'plot{key}{x}').set_data(np.array(timeData), np.array(data))


def main() -> None:
	history = 400
	at = deque(maxlen=history)
	ax = deque(maxlen=history)
	ay = deque(maxlen=history)
	az = deque(maxlen=history)

	gt = deque(maxlen=history)
	gx = deque(maxlen=history)
	gy = deque(maxlen=history)
	gz = deque(maxlen=history)

	pitch = deque(maxlen=history)
	pitch_raw = deque(maxlen=history)
	pidOut = deque(maxlen=history)

	fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)

	# Top plot
	plotAx, = axes[0].plot([], [], label="x")
	plotAy, = axes[0].plot([], [], label="y")
	plotAz, = axes[0].plot([], [], label="z")
	axes[0].set_title("Accelerometer")
	axes[0].set_ylabel("Value")
	axes[0].grid(True, alpha=0.7)
	axes[0].legend(loc="upper left")

	# Bottom plot
	plotGx, = axes[1].plot([], [], label="x")
	plotGy, = axes[1].plot([], [], label="y")
	plotGz, = axes[1].plot([], [], label="z")
	axes[1].set_title("Gyroscope")
	axes[1].set_ylabel("Value")
	axes[1].grid(True, alpha=0.7)
	axes[1].legend(loc="upper left")

	plotPitchRaw, = axes[2].plot([], [], label="raw pitch")
	plotPitch, = axes[2].plot([], [], label="pitch")
	plotPID, = axes[2].plot([], [], label="PID output")
	axes[2].set_title("Pitch")
	axes[2].set_xlabel("Time")
	axes[2].set_ylabel("Value")
	axes[2].grid(True, alpha=0.7)
	axes[2].legend(loc="upper left")

	plt.tight_layout()
	#plt.show(block=False)

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

		print("Sending code...")
		ser.write(code.encode() + b'\n')

		try:
			pitch_angle = 0.0
			PID = PIDController()
			PID.Kp = 0.1
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

							dt = 0.1
							a = accel['z']
							b = accel['x']
							g_angle = math.degrees(math.atan(a / b)) if b != 0 else 0
							if pitch_angle == 0:
								pitch_angle = g_angle
							else:
								acc_delta_angle = g_angle - pitch_angle

								gyro_delta_angle = gyro['y'] * dt

								#if sign(acc_delta_angle) != sign(gyro_delta_angle):
								#	clamped_delta = gyro_delta_angle
								#else:
								clamped_delta = sign(acc_delta_angle) * min(abs(acc_delta_angle), abs(gyro_delta_angle))
								pitch_angle += clamped_delta
							pitch.append(pitch_angle)

							#raw_pitch_angle = math.degrees(math.acos(min(1.0, accel['x'])))
							pitch_raw.append(g_angle)

							pidOut.append(PID.calcPID(pitch_angle, dt) * 1.0)

							plotPitch.set_data(np.array(at), np.array(pitch))
							plotPitchRaw.set_data(np.array(at), np.array(pitch_raw))
							plotPID.set_data(np.array(at), np.array(pidOut))
							axes[2].relim()
							axes[2].autoscale_view()
					except StopIteration:
						pass
				plt.pause(0.03)

		except Exception:
			ser.write(b'\x03\n') # CTRL-C
			ser.flush()
			raise
		
		ser.write(b'\x03\n') # CTRL-C


if __name__ == "__main__":
	main()
