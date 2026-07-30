import machine
from typing import Any, Literal


class VL53L7CX:
    """MicroPython native wrapper for the VL53L7CX time-of-flight sensor."""

    def __init__(self, i2c: machine.I2C, lpn_pin: int, i2c_rst_pin: int = -1) -> None:
        """Create a sensor instance.

        Args:
            i2c: Configured machine.I2C bus object.
            lpn_pin: LPN (low-power enable) pin number.
            i2c_rst_pin: Optional I2C reset pin number, defaults to -1.
        """
        ...

    def test_print(self, message: Any) -> None:
        """Print a test message with a VL53L7CX prefix."""
        ...

    # no dynamic allocations yet so calling this isn't strictly necessary
    def destroy(self) -> None:
        """Stop ranging (if active) and mark this object destroyed."""
        ...

    def configure(self, resolution: Literal["4x4", "8x8"], ranging_freq: int) -> int:
        """Configure resolution and ranging frequency.

        Args:
            resolution: "4x4" or "8x8".
            ranging_freq: Ranging frequency in Hz.

        Notes:
            For 4x4 resolution, frequency is clamped to [1, 60].
            For 8x8 resolution, frequency is clamped to [1, 15].

        Returns:
            Status code, where 0 means success.
        """
        ...

    def start_ranging(self) -> int:
        """Start ranging.

        Returns:
            Status code, where 0 means success.
        """
        ...

    def stop_ranging(self) -> int:
        """Stop ranging.

        Returns:
            Status code, where 0 means success.
        """
        ...

    def is_data_ready(self) -> bool:
        """Return True when a new ranging frame is ready to read."""
        ...

    def get_ranging_data(self) -> list[int | None] | None:
        """Read last distance frame.

        Returns:
            A list of per-zone distances in millimeters (length 64 or 16 depending on resolution). 
            A zone value is None when no target is detected. 
            Returns None on failure or when not currently ranging.
        """
        ...
