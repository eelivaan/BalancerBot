""" State machine to control the robot's behavior. 
    Each state is a special class that has callbacks for state transitions and
    has a tick function which returns the new state when transition is needed.
"""
from robot import BalancerBot, sign
from control import PIDController, limit


# controller for balancing
pitch_control = PIDController()
# controller for horizontal position
travel_control = PIDController()
# controller for heading direction or turning
heading_control = PIDController()

def on_config_load(config):
    """ Callback to configure the PID controllers from config file """
    pitch_control.configure(config['pid0'])
    travel_control.configure(config['pid1'])
    heading_control.configure(config['pid2'])


class StateMachine:
    state_time = 0.0    # time in seconds since last state change
    motor_signal = 0.0  # keep track of motor control signal

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
#end StateMachine


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
        bot.motors_enabled = False  # prevent accidental movements

    def tick(self, bot: BalancerBot, dt: float):
        if StateMachine.state_time > 1.5:
            pitch_offset = bot.config['pid0']['target']
            # start balancing when lifted up by external forces (helping hand)
            if abs(bot.pitch_angle.get() - pitch_offset) < 1.0:
                bot.motors_enabled = True
                return STATE_Balancing()

    def exit(self, bot: BalancerBot):
        # reset error integrals that may have accumulated while resting (although they shouldn't)
        pitch_control.err_integral, travel_control.err_integral, heading_control.err_integral = 0.0, 0.0, 0.0
        StateMachine.motor_signal = 0.0


class STATE_Raiseup(STATE_Base):
    """ The robot raises from rest to balance point  """

    def enter(self, bot: BalancerBot):
        self.direction = 1.0 if bot.pitch_angle.get() > 0.0 else -1.0
        # full speed ahead
        bot.motors_enabled = True
        bot.motor_input(self.direction, self.direction)

    def tick(self, bot: BalancerBot, dt: float):
        if StateMachine.state_time > 0.5:
            # full speed backwards after 0.5 s
            bot.motor_input(-self.direction, -self.direction)
        if abs(bot.pitch_angle.get()) < 5.0 or StateMachine.state_time > 1.0:
            # enter balancing mode when swung up
            bot.motor_input(0, 0)
            return STATE_Balancing()

    def exit(self, bot: BalancerBot):
        StateMachine.motor_signal = 0.0


class STATE_Balancing(STATE_Base):
    """ The robot holds balance and stays put without drifting """

    def enter(self, bot: BalancerBot):
        self.signal_saturation_time = 0.0
        travel_control.target_value = 0.0
        heading_control.target_value = bot.heading
        bot.travel.set(0.0)
        self.last_dist_sum = None

    def tick(self, bot: BalancerBot, dt: float):
        # wait for hand gesture
        dist_sum = sum([0.0 if d == None else d for d in bot.last_depth_measurement[0:8]])
        if self.last_dist_sum:
            #change = (self.last_dist_sum - dist_sum) / self.last_dist_sum
            if dist_sum < 2500:
                return STATE_FollowHuman()
        self.last_dist_sum = dist_sum

        # adjust pitch controller target to maintain zero travel
        pitch_control.target_value = bot.config['pid0']['target'] - travel_control.calcPID(bot.travel.get(), dt)
        # keep heading
        signal_yaw = heading_control.calcPID(bot.heading, dt)

        return self.balance(bot, dt, signal_yaw)

    def balance(self, bot: BalancerBot, dt: float, signal_yaw: float):
        """ Do the actual balancing control with common termination conditions """

        # keep balance by PID control from pitch angle and pitch derivative
        signal_pitch = pitch_control.calcPID(bot.pitch_angle.get(), dt, 
                                             -bot.pitch_deriv.get() if bot.config['use_gyro_as_D'] else None)

        # apply input to motors
        StateMachine.motor_signal = limit(StateMachine.motor_signal + signal_pitch, 1.0)
        left_motor_signal =  limit(StateMachine.motor_signal - signal_yaw, 1.0)
        right_motor_signal = limit(StateMachine.motor_signal + signal_yaw, 1.0)
        bot.motor_input(left_motor_signal, right_motor_signal)

        # stop movement when tilted too much
        if abs(bot.g_angle) > bot.config['pitch_limit']:
            return STATE_Rest()

        # stop movement when signal saturates too long
        if abs(StateMachine.motor_signal) > 0.9:
            self.signal_saturation_time += dt * 1000
            if self.signal_saturation_time > bot.config['signal_cutoff_ms']:
                return STATE_Rest()

    def exit(self, bot: BalancerBot):
        pass


class STATE_Driving(STATE_Balancing):
    """ The robot moves horizontally while keeping balance """

    def __init__(self, speed):
        self.speed = speed
        self.depth_stop_enable = True

    def enter(self, bot: BalancerBot):
        self.signal_saturation_time = 0.0
        heading_control.target_value = bot.heading

    def tick(self, bot: BalancerBot, dt: float):
        if self.depth_stop_enable:
            # stop movement when detecting obstacle in front
            if len(bot.last_depth_measurement) and bot.last_depth_measurement[5]:
                # check center pixel of the depth image
                if bot.last_depth_measurement[5] < 10 * bot.config['stop_distance_cm']:
                    return STATE_Rest()

        travel_control.target_value = self.speed
        # adjust pitch target to maintain constant movement speed
        pitch_control.target_value = bot.config['pid0']['target'] - travel_control.calcPID(bot.speed.get(), dt)
        # keep heading
        signal_yaw = heading_control.calcPID(bot.heading, dt)
        
        return super().balance(bot, dt, signal_yaw)

    def exit(self, bot: BalancerBot):
        pass


class STATE_Turning(STATE_Balancing):
    """ The robot turns in place while keeping balance """

    def __init__(self, turning_speed):
        self.turning_speed = turning_speed

    def enter(self, bot: BalancerBot):
        self.signal_saturation_time = 0.0
        travel_control.target_value = 0.0

    def tick(self, bot: BalancerBot, dt: float):
        # adjust pitch controller target to maintain zero travel
        pitch_control.target_value = bot.config['pid0']['target'] - travel_control.calcPID(bot.travel.get(), dt)

        return super().balance(bot, dt, self.turning_speed)

    def exit(self, bot: BalancerBot):
        pass


class STATE_FollowPath(STATE_Base):
    """ The robot drives the given sequence of straights and turns
        Commands:
            m<distance> Drive the specified distance (motor units)
            t<angle>    Turn the specified amount of degrees
            w<time>     Wait the given amount of seconds in balancing mode
    """

    def __init__(self, path = ['m2', 't180', 'm2', 't180']):
        self.remaining_path = path
        self.amount = 0.0

    def enter(self, bot: BalancerBot):
        self.substate = STATE_Balancing()
        self.substate.enter(bot)
        self.remaining_wait = 0.0
        bot.beep([500, 500])

    def tick(self, bot: BalancerBot, dt: float):
        if self.substate.tick(bot, dt) != None:
            # forward termination
            return STATE_Rest()

        # driving
        if isinstance(self.substate, STATE_Driving):
            if abs(bot.travel.get()) > abs(self.amount):
                self.substate.exit(bot)
                self.substate = STATE_Balancing()
                self.substate.enter(bot)

        # turning
        elif isinstance(self.substate, STATE_Turning):
            if abs(bot.headingsum) > abs(self.amount):
                self.substate.exit(bot)
                self.substate = STATE_Balancing()
                self.substate.enter(bot)

        # waiting
        elif self.remaining_wait > 0.0:
            self.remaining_wait = max(self.remaining_wait - dt, 0.0)

        # read next drive command
        elif len(self.remaining_path):
            self.substate.exit(bot)
            cmd = self.remaining_path.pop(0)
            self.amount = float(cmd[1:])
            if cmd[0] == 'm':
                self.substate = STATE_Driving(speed = 0.5 * sign(self.amount))
            elif cmd[0] == 't':
                self.substate = STATE_Turning(turning_speed = 0.1 * sign(self.amount))
            elif cmd[0] == 'w':
                self.remaining_wait = self.amount
                self.substate = STATE_Balancing()
            else:
                self.substate = STATE_Balancing()
            self.substate.enter(bot)
            bot.travel.set(0.0)
            bot.headingsum = 0.0
    #end tick

    def exit(self, bot: BalancerBot):
        self.substate.exit(bot)
#end STATE_FollowPath


class STATE_FollowHuman(STATE_Driving):
    """ The robot tries to follow the hand that is kept in its sight """

    def __init__(self):
        super().__init__(0.5)
        self.depth_stop_enable = False

    def enter(self, bot: BalancerBot):
        bot.beep([400, 600])
        super().enter(bot)

    def tick(self, bot: BalancerBot, dt: float):
        # filter the two topmost rows of depth image
        pixels_of_interest = bot.last_depth_measurement[0:8]
        closest_detection = min([1500 if d == None else d for d in pixels_of_interest])
        # check that we have a detection of the hand in any of the pixels
        if closest_detection < 400:
            # keep 20 cm distance to the target
            self.speed = limit((closest_detection - 200) * 0.01, 0.5)
        else:
            # beep a notification
            if self.speed != 0.0:
                bot.beep([800])
            self.speed = 0.0
        return super().tick(bot, dt)

    def exit(self, bot: BalancerBot):
        bot.beep([600, 400])
        super().exit(bot)