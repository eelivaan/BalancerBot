
class PIDController:

    def __init__(self) -> None:
        self.Kp, self.Kd, self.Ki = 0.0, 0.0, 0.0
        self.target_value = 0.0
        self.err_integral = 0.0
        self.prev_error = 0.0

    def configure(self, params: dict):
        """ Expecting parameters 'Kp', 'Ki', 'Kd', 'target' """
        self.Kp = params['Kp']
        self.Ki = params['Ki']
        self.Kd = params['Kd']
        self.target_value = params['target']
        self.err_integral = 0.0

    def calcPID(self, input_value, delta_time, override_derivative=None):
        err = self.target_value - input_value
        P = self.Kp * err
        I = self.Ki * self.err_integral
        if override_derivative:
            D = self.Kd * override_derivative
        else:
            D = self.Kd * (err - self.prev_error) / delta_time
        self.prev_error = err
        self.err_integral += err * delta_time
        return P + I + D