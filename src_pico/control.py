
class PIDController:

    def __init__(self) -> None:
        self.Kp, self.Kd, self.Ki = 0.0, 0.0, 0.0
        self.target_value = 0.0
        self.err_integral = 0.0
        self.prev_error = 0.0


    def calcPID(self, input_value, delta_time):
        err = self.target_value - input_value
        P = self.Kp * err
        I = self.Ki * self.err_integral
        D = self.Kd * (err - self.prev_error) / delta_time
        self.prev_error = err
        self.err_integral += err
        return P + I + D