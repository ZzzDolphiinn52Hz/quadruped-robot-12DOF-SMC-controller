from dataclasses import dataclass


MODE_STAND = 1
MODE_TROT = 4
MODE_LATERAL = 8
MODE_SPIN = 9


LEG_ORDER = ["FL", "FR", "RL", "RR"]

JOINT_ORDER = [
    "FL_hip_yaw", "FL_hip_pitch", "FL_knee_pitch",
    "FR_hip_yaw", "FR_hip_pitch", "FR_knee_pitch",
    "RL_hip_yaw", "RL_hip_pitch", "RL_knee_pitch",
    "RR_hip_yaw", "RR_hip_pitch", "RR_knee_pitch",
]
YAW_JOINTS = [
    "FL_hip_yaw",
    "FR_hip_yaw",
    "RL_hip_yaw",
    "RR_hip_yaw",
]

LEG_EFFORT_JOINTS = [
    "FL_hip_pitch",
    "FL_knee_pitch",
    "FR_hip_pitch",
    "FR_knee_pitch",
    "RL_hip_pitch",
    "RL_knee_pitch",
    "RR_hip_pitch",
    "RR_knee_pitch",
]

YAW_INDICES = [0, 3, 6, 9]
LEG_EFFORT_INDICES = [1, 2, 4, 5, 7, 8, 10, 11]

@dataclass
class RobotConfig:
    L1: float = 0.16
    L2: float = 0.16

    z_home: float = -0.26

    gait_period: float = 1.60
    duty_factor: float = 0.78
    step_height: float = 0.008
    min_step_length: float = 0.006
    max_step_length: float = 0.018
    step_length_gain: float = 0.80

    hip_pitch_min: float = -1.57
    hip_pitch_max: float = 1.57
    knee_pitch_min: float = -2.20
    knee_pitch_max: float = 0.20
    hip_yaw_min: float = -0.80
    hip_yaw_max: float = 0.80

    # Timer và timeout
    cmd_timeout: float = 0.50
    control_period: float = 0.02

    # Chiều tiến/lùi
    forward_sign: float = -1.0

    # PD effort tạm thời
    kp_hip: float = 1.60
    kd_hip: float = 0.080
    kp_knee: float = 2.20
    kd_knee: float = 0.100

    effort_limit: float = 2.80
    effort_rate_limit: float = 0.060

    position_error_limit: float = 0.70
    velocity_error_limit: float = 2.50

    hip_support_torque: float = 0.08
    knee_support_torque: float = 0.65

    effort_sign: float = -1.0