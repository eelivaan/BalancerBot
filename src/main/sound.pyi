
class Speaker:
    def __init__(self, gpio: int) -> None: 
        """ Create a Speaker instance with given GPIO pin for PWM control
        """
        ...

    def volume(self, new_volume: float = 0.5) -> float:
        """ Get or set the volume 0.0 to 1.0
        """

    def beep(self, frequency: float, duration: float) -> None:
        """ Beep for duration seconds with frequency in Hz
        """