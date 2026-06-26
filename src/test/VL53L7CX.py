"""MicroPython API for the ST VL53L7CX multizone ToF sensor.

This class mirrors the key STM32 C++ API method names for runtime use:
- start/stop ranging
- data ready polling
- ranging frame decoding
- resolution/frequency/integration/target-order/ranging-mode controls

Notes:
- Transport uses machine.I2C only.
- This is a single-class implementation intended for embedded scripts.
- Full ST ULD firmware download is performed by vl53l7cx_init().
  These binary files must be present on the Pico filesystem (extracted
  from ST's vl53l7cx_buffers.h in the ULD package):
    vl53l7cx_firmware.bin          86016 bytes  VL53L7CX_FIRMWARE
    vl53l7cx_default_config.bin      972 bytes  VL53L7CX_DEFAULT_CONFIGURATION
    vl53l7cx_default_xtalk.bin       776 bytes  VL53L7CX_DEFAULT_XTALK
"""

import struct
import time

# The macro below is used to define the number of target per zone sent
# through I2C. This value can be changed by user, in order to tune I2C
# transaction, and also the total memory size (a lower number of target per
# zone means a lower RAM). The value must be between 1 and 4.
# VL53L7CX_NB_TARGET_PER_ZONE = 1


# This buffer is used to get NVM data.
VL53L7CX_GET_NVM_CMD = bytes([
	0x54, 0x00, 0x00, 0x40,
	0x9E, 0x14, 0x00, 0xC0,
	0x9E, 0x20, 0x01, 0x40,
	0x9E, 0x34, 0x00, 0x40,
	0x9E, 0x38, 0x04, 0x04,
	0x9F, 0x38, 0x04, 0x02,
	0x9F, 0xB8, 0x01, 0x00,
	0x9F, 0xC8, 0x01, 0x00,
	0x00, 0x00, 0x00, 0x0F,
	0x02, 0x02, 0x00, 0x24
])


class VL53L7CX:
	# Public constants from the C++ API
	VL53L7CX_DEFAULT_I2C_ADDRESS = 0x52  # 8-bit ST address; 7-bit value is 0x29

	VL53L7CX_RESOLUTION_4X4 = 16
	VL53L7CX_RESOLUTION_8X8 = 64

	VL53L7CX_TARGET_ORDER_CLOSEST = 1
	VL53L7CX_TARGET_ORDER_STRONGEST = 2

	VL53L7CX_RANGING_MODE_CONTINUOUS = 1
	VL53L7CX_RANGING_MODE_AUTONOMOUS = 3

	VL53L7CX_POWER_MODE_SLEEP = 0
	VL53L7CX_POWER_MODE_WAKEUP = 1

	VL53L7CX_STATUS_OK = 0
	VL53L7CX_STATUS_TIMEOUT_ERROR = 1
	VL53L7CX_STATUS_CORRUPTED_FRAME = 2
	VL53L7CX_MCU_ERROR = 66
	VL53L7CX_STATUS_INVALID_PARAM = 127
	VL53L7CX_STATUS_ERROR = 255

	# DCI and UI command addresses
	VL53L7CX_DCI_ZONE_CONFIG = 0x5450
	VL53L7CX_DCI_FREQ_HZ = 0x5458
	VL53L7CX_DCI_INT_TIME = 0x545C
	VL53L7CX_DCI_FW_NB_TARGET = 0x5478
	VL53L7CX_DCI_RANGING_MODE = 0xAD30
	VL53L7CX_DCI_DSS_CONFIG = 0xAD38
	VL53L7CX_DCI_TARGET_ORDER = 0xAE64
	VL53L7CX_DCI_SHARPENER = 0xAED8
	VL53L7CX_DCI_SINGLE_RANGE = 0xCD5C
	VL53L7CX_DCI_OUTPUT_CONFIG = 0xCD60
	VL53L7CX_DCI_OUTPUT_ENABLES = 0xCD68
	VL53L7CX_DCI_OUTPUT_LIST = 0xCD78
	VL53L7CX_DCI_PIPE_CONTROL = 0xCF78

	VL53L7CX_UI_CMD_STATUS = 0x2C00
	VL53L7CX_UI_CMD_START = 0x2C04
	VL53L7CX_UI_CMD_END = 0x2FFF

	# Block header constants for NB_TARGET_PER_ZONE = 1
	VL53L7CX_START_BH = 0x0000000D
	VL53L7CX_METADATA_BH = 0x54B400C0
	VL53L7CX_COMMONDATA_BH = 0x54C00040
	VL53L7CX_AMBIENT_RATE_BH = 0x54D00104
	VL53L7CX_SPAD_COUNT_BH = 0x55D00404
	VL53L7CX_NB_TARGET_DETECTED_BH = 0xCF7C0401
	VL53L7CX_SIGNAL_RATE_BH = 0xCFBC0404
	VL53L7CX_RANGE_SIGMA_MM_BH = 0xD2BC0402
	VL53L7CX_DISTANCE_BH = 0xD33C0402
	VL53L7CX_REFLECTANCE_BH = 0xD43C0401
	VL53L7CX_TARGET_STATUS_BH = 0xD47C0401
	VL53L7CX_MOTION_DETECT_BH = 0xCC5008C0

	# Data block indexes
	VL53L7CX_METADATA_IDX = 0x54B4
	VL53L7CX_SPAD_COUNT_IDX = 0x55D0
	VL53L7CX_AMBIENT_RATE_IDX = 0x54D0
	VL53L7CX_NB_TARGET_DETECTED_IDX = 0xCF7C
	VL53L7CX_SIGNAL_RATE_IDX = 0xCFBC
	VL53L7CX_RANGE_SIGMA_MM_IDX = 0xD2BC
	VL53L7CX_DISTANCE_IDX = 0xD33C
	VL53L7CX_REFLECTANCE_EST_PC_IDX = 0xD43C
	VL53L7CX_TARGET_STATUS_IDX = 0xD47C
	VL53L7CX_MOTION_DETEC_IDX = 0xCC50

	def __init__(self, i2c, address=VL53L7CX_DEFAULT_I2C_ADDRESS, nb_target_per_zone=1,
				 firmware_path="vl53l7cx_firmware.bin",
				 config_path="vl53l7cx_default_config.bin",
				 xtalk_path="vl53l7cx_default_xtalk.bin"):
		"""
		Binary files required on the Pico filesystem (extract from ST ULD vl53l7cx_buffers.h):
		  firmware_path : VL53L7CX_FIRMWARE          - 86016 bytes (0x15000)
		  config_path   : VL53L7CX_DEFAULT_CONFIGURATION - 972 bytes
		  xtalk_path    : VL53L7CX_DEFAULT_XTALK      - 776 bytes
		"""
		self._i2c = i2c
		self.address = address
		self.nb_target_per_zone = int(nb_target_per_zone)
		self._fw_path   = firmware_path
		self._cfg_path  = config_path
		self._xtalk_path = xtalk_path

		self.streamcount = 255
		self.data_read_size = 0
		self._tmp = bytearray(2048)

		# Calibration buffers populated during init
		self.offset_data = bytearray(488)  # VL53L7CX_OFFSET_BUFFER_SIZE
		self.xtalk_data  = bytearray(776)  # VL53L7CX_XTALK_BUFFER_SIZE

	# ---------------------------------------------------------------------
	# Platform I2C primitives (WrByte/RdByte/WrMulti/RdMulti equivalents)
	# ---------------------------------------------------------------------
	def _write_reg(self, reg_addr, data):
		if isinstance(data, int):
			data = bytes((data & 0xFF,))
		self._i2c.writeto(self.address, struct.pack(">H", reg_addr) + data)

	def _read_reg(self, reg_addr, length=1):
		out = bytearray(length)
		self._i2c.writeto(self.address, struct.pack(">H", reg_addr), True)
		self._i2c.readfrom_into(self.address, out)
		return out

	def _wait_ms(self, ms):
		time.sleep_ms(ms)

	@staticmethod
	def _swap_buffer(buf, size):
		# ST ULD swaps endian per 32-bit word.
		end = size - (size % 4)
		for i in range(0, end, 4):
			b0 = buf[i]
			b1 = buf[i + 1]
			buf[i] = buf[i + 3]
			buf[i + 1] = buf[i + 2]
			buf[i + 2] = b1
			buf[i + 3] = b0

	def _poll_for_answer(self, size, pos, address, mask, expected_value):
		status = self.VL53L7CX_STATUS_OK
		timeout = 0
		while True:
			data = self._read_reg(address, size)
			self._tmp[:size] = data
			self._wait_ms(10)
			if timeout >= 200:
				return status | self.VL53L7CX_STATUS_TIMEOUT_ERROR
			if size >= 4 and self._tmp[2] >= 0x7F:
				return status | self.VL53L7CX_MCU_ERROR
			if (self._tmp[pos] & mask) == expected_value:
				return status
			timeout += 1

	def _write_large(self, reg_addr, data, chunk=2048):
		"""Write a large buffer in chunked I2C transactions to avoid overflow."""
		for offset in range(0, len(data), chunk):
			end = min(offset + chunk, len(data))
			self._i2c.writeto(self.address, struct.pack(">H", reg_addr + offset) + bytes(data[offset:end]))

	def _vl53l7cx_poll_for_mcu_boot(self):
		"""Poll registers 0x0006/0x0007 until the MCU firmware signals it has booted."""
		status = self.VL53L7CX_STATUS_OK
		timeout = 0
		while timeout < 500:
			go2_status0 = self._read_reg(0x0006, 1)[0]
			if (go2_status0 & 0x80) != 0:
				go2_status1 = self._read_reg(0x0007, 1)[0]
				status |= go2_status1
				break
			self._wait_ms(1)
			timeout += 1
			if (go2_status0 & 0x01) != 0:
				break
		return status

	# ---------------------------------------------------------------------
	# Public API closely matching stm32duino names
	# ---------------------------------------------------------------------
	def begin(self):
		return self.VL53L7CX_STATUS_OK

	def end(self):
		return self.vl53l7cx_stop_ranging()

	def init_sensor(self, addr=None):
		status = self.VL53L7CX_STATUS_OK
		if addr is not None:
			# Match stm32duino semantics: init_sensor() accepts 8-bit I2C addresses.
			# Accept 7-bit too for convenience and normalize to 8-bit before writing.
			if addr <= 0x7F:
				addr_8bit = (addr << 1) & 0xFE
			else:
				addr_8bit = addr & 0xFE
			if ((addr_8bit >> 1) & 0x7F) != self.address:
				status |= self.vl53l7cx_set_i2c_address(addr_8bit)
		alive = self.vl53l7cx_is_alive()
		if not alive:
			return self.VL53L7CX_STATUS_ERROR
		status |= self.vl53l7cx_init()
		return status

	def vl53l7cx_is_alive(self):
		self._write_reg(0x7FFF, 0x00)
		device_id = self._read_reg(0x0000, 1)[0]
		revision_id = self._read_reg(0x0001, 1)[0]
		self._write_reg(0x7FFF, 0x02)
		return device_id == 0xF0 and revision_id == 0x02

	def vl53l7cx_init(self):
		"""Full init: SW reboot → firmware download → MCU boot → NVM/xtalk/config upload."""
		status = self.VL53L7CX_STATUS_OK

		# ------------------------------------------------------------------
		# SW reboot sequence
		# ------------------------------------------------------------------
		self._write_reg(0x7FFF, 0x00)
		self._write_reg(0x0009, 0x04)
		self._write_reg(0x000F, 0x40)
		self._write_reg(0x000A, 0x03)
		self._read_reg(0x7FFF, 1)   # dummy read (mirrors C++ RdByte)
		self._write_reg(0x000C, 0x01)
		self._write_reg(0x0101, 0x00)
		self._write_reg(0x0102, 0x00)
		self._write_reg(0x010A, 0x01)
		self._write_reg(0x4002, 0x01)
		self._write_reg(0x4002, 0x00)
		self._write_reg(0x010A, 0x03)
		self._write_reg(0x0103, 0x01)
		self._write_reg(0x000C, 0x00)
		self._write_reg(0x000F, 0x43)
		self._wait_ms(1)
		self._write_reg(0x000F, 0x40)
		self._write_reg(0x000A, 0x01)
		self._wait_ms(100)

		# Wait for sensor to boot
		self._write_reg(0x7FFF, 0x00)
		status |= self._poll_for_answer(1, 0, 0x0006, 0xFF, 0x01)
		if status:
			return status

		self._write_reg(0x000E, 0x01)
		self._write_reg(0x7FFF, 0x02)

		# Enable FW access
		self._write_reg(0x0003, 0x0D)
		self._write_reg(0x7FFF, 0x01)
		status |= self._poll_for_answer(1, 0, 0x0021, 0x10, 0x10)
		self._write_reg(0x7FFF, 0x00)

		# Enable host access to GO1
		self._read_reg(0x7FFF, 1)   # dummy read
		self._write_reg(0x000C, 0x01)

		# Power ON status sequence
		self._write_reg(0x7FFF, 0x00)
		self._write_reg(0x0101, 0x00)
		self._write_reg(0x0102, 0x00)
		self._write_reg(0x010A, 0x01)
		self._write_reg(0x4002, 0x01)
		self._write_reg(0x4002, 0x00)
		self._write_reg(0x010A, 0x03)
		self._write_reg(0x0103, 0x01)
		self._write_reg(0x400F, 0x00)
		self._write_reg(0x021A, 0x43)
		self._write_reg(0x021A, 0x03)
		self._write_reg(0x021A, 0x01)
		self._write_reg(0x021A, 0x00)
		self._write_reg(0x0219, 0x00)
		self._write_reg(0x021B, 0x00)

		# Wake up MCU
		self._write_reg(0x7FFF, 0x00)
		self._read_reg(0x7FFF, 1)   # dummy read
		self._write_reg(0x000C, 0x00)
		self._write_reg(0x7FFF, 0x01)
		self._write_reg(0x0020, 0x07)
		self._write_reg(0x0020, 0x06)

		# ------------------------------------------------------------------
		# Download firmware from binary file in three paged 2-byte-addressed
		# windows: page 0x09 (0x0000–0x7FFF), 0x0A (0x0000–0x7FFF),
		# 0x0B (0x0000–0x4FFF).  Read directly from file to avoid loading
		# the full 84 KB blob into RAM at once.
		# ------------------------------------------------------------------
		_FW_CHUNK = 2048
		_PAGES = ((0x09, 0x8000), (0x0A, 0x8000), (0x0B, 0x5000))
		with open(self._fw_path, "rb") as fw_file:
			for page, size in _PAGES:
				self._write_reg(0x7FFF, page)
				offset = 0
				while offset < size:
					n = min(_FW_CHUNK, size - offset)
					chunk = fw_file.read(n)
					self._i2c.writeto(self.address, struct.pack(">H", offset) + chunk)
					offset += n
		self._write_reg(0x7FFF, 0x01)

		# Verify firmware downloaded correctly
		self._write_reg(0x7FFF, 0x02)
		self._write_reg(0x0003, 0x0D)
		self._write_reg(0x7FFF, 0x01)
		status |= self._poll_for_answer(1, 0, 0x0021, 0x10, 0x10)
		if status:
			return status

		self._write_reg(0x7FFF, 0x00)
		self._read_reg(0x7FFF, 1)   # dummy read
		self._write_reg(0x000C, 0x01)

		# ------------------------------------------------------------------
		# Reset MCU and wait for boot
		# ------------------------------------------------------------------
		self._write_reg(0x7FFF, 0x00)
		self._write_reg(0x0114, 0x00)
		self._write_reg(0x0115, 0x00)
		self._write_reg(0x0116, 0x42)
		self._write_reg(0x0117, 0x00)
		self._write_reg(0x000B, 0x00)
		self._read_reg(0x7FFF, 1)   # dummy read
		self._write_reg(0x000C, 0x00)
		self._write_reg(0x000B, 0x01)
		status |= self._vl53l7cx_poll_for_mcu_boot()
		if status:
			return status

		self._write_reg(0x7FFF, 0x02)

		# ------------------------------------------------------------------
		# Read factory offset calibration from NVM
		# ------------------------------------------------------------------
		self._write_large(0x2FD8, VL53L7CX_GET_NVM_CMD)
		# NVM read completes with status byte == 2 (not 3 as with DCI commands)
		status |= self._poll_for_answer(4, 0, self.VL53L7CX_UI_CMD_STATUS, 0xFF, 0x02)
		nvm_buf = bytes(self._read_reg(self.VL53L7CX_UI_CMD_START, 492))
		self.offset_data[:] = nvm_buf[:488]
		status |= self._vl53l7cx_send_offset_data(self.VL53L7CX_RESOLUTION_4X4)

		# ------------------------------------------------------------------
		# Load default xtalk and send to sensor
		# ------------------------------------------------------------------
		with open(self._xtalk_path, "rb") as f:
			self.xtalk_data[:] = f.read()
		status |= self._vl53l7cx_send_xtalk_data(self.VL53L7CX_RESOLUTION_4X4)

		# ------------------------------------------------------------------
		# Send default sensor configuration
		# ------------------------------------------------------------------
		with open(self._cfg_path, "rb") as f:
			cfg = f.read()
		self._write_large(0x2C34, cfg)
		status |= self._poll_for_answer(4, 1, self.VL53L7CX_UI_CMD_STATUS, 0xFF, 0x03)

		# Configure pipe control (targets per zone)
		pipe_ctrl = bytes([self.nb_target_per_zone, 0x00, 0x01, 0x00])
		status |= self.vl53l7cx_dci_write_data(pipe_ctrl, self.VL53L7CX_DCI_PIPE_CONTROL, 4)

		# If more than 1 target per zone, update the firmware's internal count
		if self.nb_target_per_zone != 1:
			status |= self.vl53l7cx_dci_replace_data(
				self.VL53L7CX_DCI_FW_NB_TARGET, 16,
				bytes([self.nb_target_per_zone]), 0x0C)

		single_range = struct.pack("<I", 0x01)
		status |= self.vl53l7cx_dci_write_data(single_range, self.VL53L7CX_DCI_SINGLE_RANGE, 4)
		return status

	def vl53l7cx_set_i2c_address(self, i2c_address_8bit):
		self._write_reg(0x7FFF, 0x00)
		self._write_reg(0x0004, (i2c_address_8bit >> 1) & 0x7F)
		self.address = (i2c_address_8bit >> 1) & 0x7F
		self._write_reg(0x7FFF, 0x02)
		return self.VL53L7CX_STATUS_OK

	def vl53l7cx_get_power_mode(self):
		status = self.VL53L7CX_STATUS_OK
		self._write_reg(0x7FFF, 0x00)
		tmp = self._read_reg(0x0009, 1)[0]
		if tmp == 0x04:
			mode = self.VL53L7CX_POWER_MODE_WAKEUP
		elif tmp == 0x02:
			mode = self.VL53L7CX_POWER_MODE_SLEEP
		else:
			mode = 0
			status |= self.VL53L7CX_STATUS_ERROR
		self._write_reg(0x7FFF, 0x02)
		return status, mode

	def vl53l7cx_set_power_mode(self, power_mode):
		status, current = self.vl53l7cx_get_power_mode()
		if power_mode == current:
			return status

		if power_mode == self.VL53L7CX_POWER_MODE_WAKEUP:
			self._write_reg(0x7FFF, 0x00)
			self._write_reg(0x0009, 0x04)
			status |= self._poll_for_answer(1, 0, 0x0006, 0x01, 0x01)
		elif power_mode == self.VL53L7CX_POWER_MODE_SLEEP:
			self._write_reg(0x7FFF, 0x00)
			self._write_reg(0x0009, 0x02)
			status |= self._poll_for_answer(1, 0, 0x0006, 0x01, 0x00)
		else:
			return self.VL53L7CX_STATUS_ERROR

		self._write_reg(0x7FFF, 0x02)
		return status

	def vl53l7cx_start_ranging(self):
		status = self.VL53L7CX_STATUS_OK
		resolution = self.vl53l7cx_get_resolution()[1]

		output_bh_enable = [0x00000007, 0x00000000, 0x00000000, 0xC0000000]
		output_bh_enable[0] += 8 + 16 + 32 + 64 + 128 + 256 + 512 + 1024 + 2048

		output = [
			self.VL53L7CX_START_BH,
			self.VL53L7CX_METADATA_BH,
			self.VL53L7CX_COMMONDATA_BH,
			self.VL53L7CX_AMBIENT_RATE_BH,
			self.VL53L7CX_SPAD_COUNT_BH,
			self.VL53L7CX_NB_TARGET_DETECTED_BH,
			self.VL53L7CX_SIGNAL_RATE_BH,
			self.VL53L7CX_RANGE_SIGMA_MM_BH,
			self.VL53L7CX_DISTANCE_BH,
			self.VL53L7CX_REFLECTANCE_BH,
			self.VL53L7CX_TARGET_STATUS_BH,
			self.VL53L7CX_MOTION_DETECT_BH,
		]

		self.data_read_size = 0
		self.streamcount = 255

		for i, val in enumerate(output):
			if val == 0 or (output_bh_enable[i // 32] & (1 << (i % 32))) == 0:
				continue
			bh_type = val & 0xF
			bh_size = (val >> 4) & 0x0FFF
			bh_idx = (val >> 16) & 0xFFFF
			if 0x01 <= bh_type < 0x0D:
				if 0x54D0 <= bh_idx < (0x54D0 + 960):
					bh_size = resolution
				else:
					bh_size = resolution * self.nb_target_per_zone
				self.data_read_size += bh_type * bh_size
			else:
				self.data_read_size += bh_size
			self.data_read_size += 4
		self.data_read_size += 24

		status |= self.vl53l7cx_dci_write_data(self._pack_u32_list(output), self.VL53L7CX_DCI_OUTPUT_LIST, 4 * len(output))

		# Keep upstream count behavior (loop index + 1 == len(output) + 1).
		header_config = [self.data_read_size, len(output) + 1]
		status |= self.vl53l7cx_dci_write_data(self._pack_u32_list(header_config), self.VL53L7CX_DCI_OUTPUT_CONFIG, 8)
		status |= self.vl53l7cx_dci_write_data(self._pack_u32_list(output_bh_enable), self.VL53L7CX_DCI_OUTPUT_ENABLES, 16)

		self._write_reg(0x7FFF, 0x00)
		self._write_reg(0x0009, 0x05)
		self._write_reg(0x7FFF, 0x02)

		cmd = bytes((0x00, 0x03, 0x00, 0x00))
		self._write_reg(self.VL53L7CX_UI_CMD_END - 3, cmd)
		status |= self._poll_for_answer(4, 1, self.VL53L7CX_UI_CMD_STATUS, 0xFF, 0x03)

		status2, d = self.vl53l7cx_dci_read_data(0x5440, 12)
		status |= status2
		expected = struct.unpack("<I", d[8:12])[0]
		if expected != self.data_read_size:
			status |= self.VL53L7CX_STATUS_ERROR
		return status

	def vl53l7cx_stop_ranging(self):
		status = self.VL53L7CX_STATUS_OK
		auto_stop_flag = struct.unpack("<I", self._read_reg(0x2FFC, 4))[0]
		if auto_stop_flag != 0x4FF:
			self._write_reg(0x7FFF, 0x00)
			self._write_reg(0x0015, 0x16)
			self._write_reg(0x0014, 0x01)
			timeout = 0
			while True:
				tmp = self._read_reg(0x0006, 1)[0]
				self._wait_ms(10)
				timeout += 1
				if ((tmp & 0x80) >> 7) != 0:
					break
				if timeout > 500:
					status |= tmp
					break

		tmp = self._read_reg(0x0006, 1)[0]
		if (tmp & 0x80) != 0:
			tmp2 = self._read_reg(0x0007, 1)[0]
			if tmp2 not in (0x84, 0x85):
				status |= tmp2

		self._write_reg(0x7FFF, 0x00)
		self._write_reg(0x0014, 0x00)
		self._write_reg(0x0015, 0x00)
		self._write_reg(0x0009, 0x04)
		self._write_reg(0x7FFF, 0x02)
		return status

	def vl53l7cx_check_data_ready(self):
		status = self.VL53L7CX_STATUS_OK
		d = self._read_reg(0x0000, 4)
		is_ready = 0
		if (
			d[0] != self.streamcount
			and d[0] != 255
			and d[1] == 0x05
			and (d[2] & 0x05) == 0x05
			and (d[3] & 0x10) == 0x10
		):
			is_ready = 1
			self.streamcount = d[0]
		else:
			if (d[3] & 0x80) != 0:
				status |= d[2]
			is_ready = 0
		return status, is_ready

	def vl53l7cx_get_ranging_data(self):
		status = self.VL53L7CX_STATUS_OK
		if self.data_read_size <= 0:
			return self.VL53L7CX_STATUS_ERROR, None

		buf = self._read_reg(0x0000, self.data_read_size)
		self.streamcount = buf[0]
		self._swap_buffer(buf, self.data_read_size)

		results = {
			"streamcount": self.streamcount,
			"silicon_temp_degc": 0,
			"ambient_per_spad": [],
			"nb_target_detected": [],
			"nb_spads_enabled": [],
			"signal_per_spad": [],
			"range_sigma_mm": [],
			"distance_mm": [],
			"reflectance": [],
			"target_status": [],
			"motion_indicator": None,
		}

		i = 16
		while i < self.data_read_size:
			bh = struct.unpack_from("<I", buf, i)[0]
			bh_type = bh & 0xF
			bh_size = (bh >> 4) & 0x0FFF
			bh_idx = (bh >> 16) & 0xFFFF
			if 0x01 < bh_type < 0x0D:
				msize = bh_type * bh_size
			else:
				msize = bh_size
			payload = buf[i + 4 : i + 4 + msize]

			if bh_idx == self.VL53L7CX_METADATA_IDX and len(buf) > i + 12:
				t = buf[i + 12]
				results["silicon_temp_degc"] = t - 256 if t > 127 else t
			elif bh_idx == self.VL53L7CX_AMBIENT_RATE_IDX:
				results["ambient_per_spad"] = self._u32_list(payload)
			elif bh_idx == self.VL53L7CX_SPAD_COUNT_IDX:
				results["nb_spads_enabled"] = self._u32_list(payload)
			elif bh_idx == self.VL53L7CX_NB_TARGET_DETECTED_IDX:
				results["nb_target_detected"] = list(payload)
			elif bh_idx == self.VL53L7CX_SIGNAL_RATE_IDX:
				results["signal_per_spad"] = self._u32_list(payload)
			elif bh_idx == self.VL53L7CX_RANGE_SIGMA_MM_IDX:
				results["range_sigma_mm"] = self._u16_list(payload)
			elif bh_idx == self.VL53L7CX_DISTANCE_IDX:
				results["distance_mm"] = self._s16_list(payload)
			elif bh_idx == self.VL53L7CX_REFLECTANCE_EST_PC_IDX:
				results["reflectance"] = list(payload)
			elif bh_idx == self.VL53L7CX_TARGET_STATUS_IDX:
				results["target_status"] = list(payload)
			elif bh_idx == self.VL53L7CX_MOTION_DETEC_IDX:
				results["motion_indicator"] = payload

			i += 4 + msize

		for idx, v in enumerate(results["ambient_per_spad"]):
			results["ambient_per_spad"][idx] = v // 2048
		for idx, v in enumerate(results["distance_mm"]):
			dv = v // 4
			results["distance_mm"][idx] = 0 if dv < 0 else dv
		for idx, v in enumerate(results["reflectance"]):
			results["reflectance"][idx] = v // 2
		for idx, v in enumerate(results["range_sigma_mm"]):
			results["range_sigma_mm"][idx] = v // 128
		for idx, v in enumerate(results["signal_per_spad"]):
			results["signal_per_spad"][idx] = v // 2048
		if results["motion_indicator"] is not None and len(results["motion_indicator"]) % 4 == 0:
			motion = self._u32_list(results["motion_indicator"])
			for idx in range(min(32, len(motion))):
				motion[idx] = motion[idx] // 65535
			results["motion_indicator"] = motion

		if results["nb_target_detected"] and results["target_status"]:
			for z, detected in enumerate(results["nb_target_detected"]):
				if detected == 0:
					for t in range(self.nb_target_per_zone):
						pos = z * self.nb_target_per_zone + t
						if pos < len(results["target_status"]):
							results["target_status"][pos] = 255

		header_id = ((buf[0x08] << 8) & 0xFF00) | (buf[0x09] & 0xFF)
		footer_id = ((buf[self.data_read_size - 4] << 8) & 0xFF00) | (buf[self.data_read_size - 3] & 0xFF)
		if header_id != footer_id:
			status |= self.VL53L7CX_STATUS_CORRUPTED_FRAME

		return status, results

	def vl53l7cx_get_resolution(self):
		status, d = self.vl53l7cx_dci_read_data(self.VL53L7CX_DCI_ZONE_CONFIG, 8)
		return status, d[0] * d[1]

	def vl53l7cx_set_resolution(self, resolution):
		status = self.VL53L7CX_STATUS_OK
		if resolution == self.VL53L7CX_RESOLUTION_4X4:
			status, dss = self.vl53l7cx_dci_read_data(self.VL53L7CX_DCI_DSS_CONFIG, 16)
			dss = bytearray(dss)
			dss[0x04], dss[0x06], dss[0x09] = 64, 64, 4
			status |= self.vl53l7cx_dci_write_data(dss, self.VL53L7CX_DCI_DSS_CONFIG, 16)

			status2, zone = self.vl53l7cx_dci_read_data(self.VL53L7CX_DCI_ZONE_CONFIG, 8)
			status |= status2
			zone = bytearray(zone)
			zone[0x00], zone[0x01], zone[0x04], zone[0x05] = 4, 4, 8, 8
			status |= self.vl53l7cx_dci_write_data(zone, self.VL53L7CX_DCI_ZONE_CONFIG, 8)
		elif resolution == self.VL53L7CX_RESOLUTION_8X8:
			status, dss = self.vl53l7cx_dci_read_data(self.VL53L7CX_DCI_DSS_CONFIG, 16)
			dss = bytearray(dss)
			dss[0x04], dss[0x06], dss[0x09] = 16, 16, 1
			status |= self.vl53l7cx_dci_write_data(dss, self.VL53L7CX_DCI_DSS_CONFIG, 16)

			status2, zone = self.vl53l7cx_dci_read_data(self.VL53L7CX_DCI_ZONE_CONFIG, 8)
			status |= status2
			zone = bytearray(zone)
			zone[0x00], zone[0x01], zone[0x04], zone[0x05] = 8, 8, 4, 4
			status |= self.vl53l7cx_dci_write_data(zone, self.VL53L7CX_DCI_ZONE_CONFIG, 8)
		else:
			return self.VL53L7CX_STATUS_INVALID_PARAM
		status |= self._vl53l7cx_send_offset_data(resolution)
		status |= self._vl53l7cx_send_xtalk_data(resolution)
		return status

	def vl53l7cx_get_ranging_frequency_hz(self):
		status, d = self.vl53l7cx_dci_read_data(self.VL53L7CX_DCI_FREQ_HZ, 4)
		return status, d[1]

	def vl53l7cx_set_ranging_frequency_hz(self, frequency_hz):
		return self.vl53l7cx_dci_replace_data(self.VL53L7CX_DCI_FREQ_HZ, 4, bytes((frequency_hz & 0xFF,)), 0x01)

	def vl53l7cx_get_integration_time_ms(self):
		status, d = self.vl53l7cx_dci_read_data(self.VL53L7CX_DCI_INT_TIME, 20)
		v = struct.unpack("<I", d[0:4])[0] // 1000
		return status, v

	def vl53l7cx_set_integration_time_ms(self, integration_time_ms):
		if integration_time_ms < 2 or integration_time_ms > 1000:
			return self.VL53L7CX_STATUS_INVALID_PARAM
		v = struct.pack("<I", integration_time_ms * 1000)
		return self.vl53l7cx_dci_replace_data(self.VL53L7CX_DCI_INT_TIME, 20, v, 0x00)

	def vl53l7cx_get_sharpener_percent(self):
		status, d = self.vl53l7cx_dci_read_data(self.VL53L7CX_DCI_SHARPENER, 16)
		return status, (d[0x0D] * 100) // 255

	def vl53l7cx_set_sharpener_percent(self, sharpener_percent):
		if sharpener_percent >= 100:
			return self.VL53L7CX_STATUS_INVALID_PARAM
		sharp = (sharpener_percent * 255) // 100
		return self.vl53l7cx_dci_replace_data(self.VL53L7CX_DCI_SHARPENER, 16, bytes((sharp & 0xFF,)), 0x0D)

	def vl53l7cx_get_target_order(self):
		status, d = self.vl53l7cx_dci_read_data(self.VL53L7CX_DCI_TARGET_ORDER, 4)
		return status, d[0]

	def vl53l7cx_set_target_order(self, target_order):
		if target_order not in (self.VL53L7CX_TARGET_ORDER_CLOSEST, self.VL53L7CX_TARGET_ORDER_STRONGEST):
			return self.VL53L7CX_STATUS_INVALID_PARAM
		return self.vl53l7cx_dci_replace_data(self.VL53L7CX_DCI_TARGET_ORDER, 4, bytes((target_order & 0xFF,)), 0x00)

	def vl53l7cx_get_ranging_mode(self):
		status, d = self.vl53l7cx_dci_read_data(self.VL53L7CX_DCI_RANGING_MODE, 8)
		if d[0x01] == 0x01:
			return status, self.VL53L7CX_RANGING_MODE_CONTINUOUS
		return status, self.VL53L7CX_RANGING_MODE_AUTONOMOUS

	def vl53l7cx_set_ranging_mode(self, ranging_mode):
		status, d = self.vl53l7cx_dci_read_data(self.VL53L7CX_DCI_RANGING_MODE, 8)
		d = bytearray(d)
		if ranging_mode == self.VL53L7CX_RANGING_MODE_CONTINUOUS:
			d[0x01] = 0x01
			d[0x03] = 0x03
			single_range = struct.pack("<I", 0x00)
		elif ranging_mode == self.VL53L7CX_RANGING_MODE_AUTONOMOUS:
			d[0x01] = 0x03
			d[0x03] = 0x02
			single_range = struct.pack("<I", 0x01)
		else:
			return self.VL53L7CX_STATUS_INVALID_PARAM

		status |= self.vl53l7cx_dci_write_data(d, self.VL53L7CX_DCI_RANGING_MODE, 8)
		status |= self.vl53l7cx_dci_write_data(single_range, self.VL53L7CX_DCI_SINGLE_RANGE, 4)
		return status

	# ---------------------------------------------------------------------
	# Inner calibration helpers (mirrors C++ _vl53l7cx_send_offset/xtalk_data)
	# ---------------------------------------------------------------------
	def _vl53l7cx_send_offset_data(self, resolution):
		_DSS_4X4 = bytes([0x0F, 0x04, 0x04, 0x00, 0x08, 0x10, 0x10, 0x07])
		_FOOTER  = bytes([0x00, 0x00, 0x00, 0x0F, 0x03, 0x01, 0x01, 0xE4])
		OFFSET_SIZE = 488  # VL53L7CX_OFFSET_BUFFER_SIZE

		tmp = bytearray(self.offset_data)
		if resolution == self.VL53L7CX_RESOLUTION_4X4:
			tmp[0x10:0x18] = _DSS_4X4
			self._swap_buffer(tmp, OFFSET_SIZE)
			signal_grid = list(struct.unpack_from("<64I", tmp, 0x3C))
			range_grid  = list(struct.unpack_from("<64h", tmp, 0x140))
			for j in range(4):
				for i in range(4):
					signal_grid[i + 4 * j] = (
						signal_grid[(2 * i) + (16 * j)] +
						signal_grid[(2 * i) + (16 * j) + 1] +
						signal_grid[(2 * i) + (16 * j) + 8] +
						signal_grid[(2 * i) + (16 * j) + 9]
					) // 4
					range_grid[i + 4 * j] = (
						range_grid[(2 * i) + (16 * j)] +
						range_grid[(2 * i) + (16 * j) + 1] +
						range_grid[(2 * i) + (16 * j) + 8] +
						range_grid[(2 * i) + (16 * j) + 9]
					) // 4
			for k in range(0x10, 64):
				signal_grid[k] = 0
				range_grid[k] = 0
			struct.pack_into("<64I", tmp, 0x3C, *signal_grid)
			struct.pack_into("<64h", tmp, 0x140, *range_grid)
			self._swap_buffer(tmp, OFFSET_SIZE)

		# Shift payload left by 8 bytes (remove DCI header) without reading past buffer end.
		for k in range(OFFSET_SIZE - 8):
			tmp[k] = tmp[k + 8]
		tmp[0x1E0:0x1E8] = _FOOTER  # 0x1E0 == 480

		self._write_large(0x2E18, tmp)
		return self._poll_for_answer(4, 1, self.VL53L7CX_UI_CMD_STATUS, 0xFF, 0x03)

	def _vl53l7cx_send_xtalk_data(self, resolution):
		_RES_4X4     = bytes([0x0F, 0x04, 0x04, 0x17, 0x08, 0x10, 0x10, 0x07])
		_DSS_4X4     = bytes([0x00, 0x78, 0x00, 0x08, 0x00, 0x00, 0x00, 0x08])
		_PROFILE_4X4 = bytes([0xA0, 0xFC, 0x01, 0x00])
		XTALK_SIZE = 776  # VL53L7CX_XTALK_BUFFER_SIZE

		tmp = bytearray(self.xtalk_data)
		if resolution == self.VL53L7CX_RESOLUTION_4X4:
			tmp[0x08:0x10] = _RES_4X4
			tmp[0x20:0x28] = _DSS_4X4
			self._swap_buffer(tmp, XTALK_SIZE)
			signal_grid = list(struct.unpack_from("<64I", tmp, 0x34))
			for j in range(4):
				for i in range(4):
					signal_grid[i + 4 * j] = (
						signal_grid[(2 * i) + (16 * j)] +
						signal_grid[(2 * i) + (16 * j) + 1] +
						signal_grid[(2 * i) + (16 * j) + 8] +
						signal_grid[(2 * i) + (16 * j) + 9]
					) // 4
			for k in range(0x10, 64):
				signal_grid[k] = 0
			struct.pack_into("<64I", tmp, 0x34, *signal_grid)
			self._swap_buffer(tmp, XTALK_SIZE)
			tmp[0x134:0x138] = _PROFILE_4X4
			tmp[0x078:0x07C] = bytes(4)

		self._write_large(0x2CF8, tmp)
		return self._poll_for_answer(4, 1, self.VL53L7CX_UI_CMD_STATUS, 0xFF, 0x03)

	# ---------------------------------------------------------------------
	# DCI helpers
	# ---------------------------------------------------------------------
	def vl53l7cx_dci_read_data(self, index, data_size):
		status = self.VL53L7CX_STATUS_OK
		rd_size = data_size + 12
		if rd_size > len(self._tmp):
			return self.VL53L7CX_STATUS_ERROR, bytes()
		cmd = bytearray((0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0F, 0x00, 0x02, 0x00, 0x08))
		cmd[0] = (index >> 8) & 0xFF
		cmd[1] = index & 0xFF
		cmd[2] = ((data_size & 0xFF0) >> 4) & 0xFF
		cmd[3] = ((data_size & 0x00F) << 4) & 0xFF

		self._write_reg(self.VL53L7CX_UI_CMD_END - 11, cmd)
		status |= self._poll_for_answer(4, 1, self.VL53L7CX_UI_CMD_STATUS, 0xFF, 0x03)

		fw = bytearray(self._read_reg(self.VL53L7CX_UI_CMD_START, rd_size))
		self._swap_buffer(fw, rd_size)
		return status, bytes(fw[4 : 4 + data_size])

	def vl53l7cx_dci_write_data(self, data, index, data_size):
		status = self.VL53L7CX_STATUS_OK
		if (data_size + 12) > len(self._tmp):
			return self.VL53L7CX_STATUS_ERROR
		data = bytearray(data[:data_size])
		headers = bytearray(4)
		footer = bytearray((0x00, 0x00, 0x00, 0x0F, 0x05, 0x01, ((data_size + 8) >> 8) & 0xFF, (data_size + 8) & 0xFF))
		address = self.VL53L7CX_UI_CMD_END - (data_size + 12) + 1

		headers[0] = (index >> 8) & 0xFF
		headers[1] = index & 0xFF
		headers[2] = ((data_size & 0xFF0) >> 4) & 0xFF
		headers[3] = ((data_size & 0x00F) << 4) & 0xFF

		self._swap_buffer(data, data_size)
		fw = bytearray(data_size + 12)
		fw[0:4] = headers
		fw[4 : 4 + data_size] = data
		fw[4 + data_size : 12 + data_size] = footer

		self._write_reg(address, fw)
		status |= self._poll_for_answer(4, 1, self.VL53L7CX_UI_CMD_STATUS, 0xFF, 0x03)
		return status

	def vl53l7cx_dci_replace_data(self, index, data_size, new_data, new_data_pos):
		status, data = self.vl53l7cx_dci_read_data(index, data_size)
		patched = bytearray(data)
		patched[new_data_pos : new_data_pos + len(new_data)] = new_data
		status |= self.vl53l7cx_dci_write_data(patched, index, data_size)
		return status

	# ---------------------------------------------------------------------
	# Small conversion helpers
	# ---------------------------------------------------------------------
	@staticmethod
	def _pack_u32_list(vals):
		out = bytearray(4 * len(vals))
		for i, v in enumerate(vals):
			struct.pack_into("<I", out, i * 4, int(v) & 0xFFFFFFFF)
		return out

	@staticmethod
	def _u32_list(buf):
		n = len(buf) // 4
		return [struct.unpack_from("<I", buf, i * 4)[0] for i in range(n)]

	@staticmethod
	def _u16_list(buf):
		n = len(buf) // 2
		return [struct.unpack_from("<H", buf, i * 2)[0] for i in range(n)]

	@staticmethod
	def _s16_list(buf):
		n = len(buf) // 2
		return [struct.unpack_from("<h", buf, i * 2)[0] for i in range(n)]
