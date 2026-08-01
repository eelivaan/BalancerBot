""" State machine for the robot. 
    Each state is a function that ticks regularly and returns the new state.
"""
from robot import BalancerBot
from control import PIDController, limit


# controller for balancing
pitch_control = PIDController()
# controller for horizontal position
travel_control = PIDController()
# controller for heading direction or turning
heading_control = PIDController()

def on_config_load(config):
    """ Callback to configure PID controllers from config file """
    pitch_control.configure(config['pid0'])
    travel_control.configure(config['pid1'])
    heading_control.configure(config['pid2'])

#def reset_control():
#    global motor_traversal, motor_signal
#    bot.motors_enabled = True
#    pitch_control.err_integral, travel_control.err_integral, heading_control.err_integral = 0.0, 0.0, 0.0
#    motor_traversal = 0.0
#    motor_signal = 0.0
#    bot.heading = 0.0


class StateMachine:
    state_time = 0.0  # time in seconds since state change

    def __init__(self, bot: BalancerBot):
        self.bot = bot
        self.cur_state = None

    def change_state(self, new_state):
        if self.cur_state:
            self.cur_state.exit(self.bot)
        self.cur_state = new_state
        if self.cur_state:
            self.cur_state.enter(self.bot)
        StateMachine.state_time = 0

    def update(self, dt: float):
        if self.cur_state:
            StateMachine.state_time += dt
            # tick current state
            if new_state := self.cur_state.tick(self.bot, dt):
                # transition if needed
                self.change_state(new_state)
    #end update


class STATE_Base:
    """ Base class for states with callbacks for state transitions and ticking """

    def enter(self, bot: BalancerBot):
        pass

    def tick(self, bot: BalancerBot, dt: float):
        pass

    def exit(self, bot: BalancerBot):
        pass


class STATE_Rest(STATE_Base):
    """ The robot rests at ground with motors off """

    def enter(self, bot: BalancerBot):
        # stop any movement
        bot.motor_input(0, 0)

    def tick(self, bot: BalancerBot, dt: float):
        if StateMachine.state_time > 2.0:
            pitch_offset = bot.config['pid0']['target']
            # start balancing when lifted up by external forces (hand)
            if abs(bot.pitch_angle.get() - pitch_offset) < 1.0:
                return STATE_Balancing()

    def exit(self, bot: BalancerBot):
        pass


class STATE_Raiseup(STATE_Base):
    """ The robot raises from rest to balance point  """


class STATE_Balancing(STATE_Base):
    """ The robot holds balance and stays put without drifting """

    def enter(self, bot: BalancerBot):
        self.motor_signal = 0.0
        self.signal_saturation_time = 0.0
        pitch_control.err_integral, travel_control.err_integral, heading_control.err_integral = 0.0, 0.0, 0.0

    def tick(self, bot: BalancerBot, dt: float):
        pitch_offset = bot.config['pid0']['target']
        
        # adjust pitch controller target to maintain zero travel
        if not isinstance(self, STATE_Driving):
            pitch_control.target_value = pitch_offset - travel_control.calcPID(bot.travel, dt)
        # keep balance by PID control from pitch angle and pitch derivative
        signal_pitch = pitch_control.calcPID(bot.pitch_angle.get(), dt, -bot.pitch_deriv.get() if bot.config['use_gyro_as_D'] else None)
        # keep heading
        signal_yaw = heading_control.calcPID(bot.heading, dt)

        # apply input to motors
        self.motor_signal = limit(self.motor_signal + signal_pitch, 1.0)
        left_motor_signal =  limit(self.motor_signal - signal_yaw, 1.0)
        right_motor_signal = limit(self.motor_signal + signal_yaw, 1.0)
        bot.motor_input(left_motor_signal, right_motor_signal)

        # stop movement when detecting object
        if len(bot.last_depth_measurement) and bot.last_depth_measurement[5]:
            # check center pixel
            if bot.last_depth_measurement[5] < 10*bot.config['stop_distance_cm']:
                return STATE_Rest()

        # stop movement when tilted too much
        if abs(bot.g_angle) > bot.config['pitch_limit']:
            return STATE_Rest()

        # stop movement when signal saturates too long
        if abs(self.motor_signal) > 0.9:
            self.signal_saturation_time += dt * 1000
            if self.signal_saturation_time > bot.config['signal_cutoff_ms']:
                return STATE_Rest()

    def exit(self, bot: BalancerBot):
        pass


class STATE_Driving(STATE_Balancing):
    """ The robot moves horizontally while keeping balance """

    def enter(self, bot: BalancerBot):
        super().enter(bot)

    def tick(self, bot: BalancerBot, dt: float):
        pitch_offset = bot.config['pid0']['target']
        # adjust pitch target to maintain constant movement speed
        pitch_control.target_value = pitch_offset - travel_control.calcPID(bot.speed.get(), dt)
        return super().tick(bot, dt)

    def exit(self, bot: BalancerBot):
        super().exit(bot)
