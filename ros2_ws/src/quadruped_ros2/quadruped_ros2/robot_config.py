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


@dataclass
class RobotConfig:
    # Link length
    L1: float = 0.16
    L2: float = 0.16

    # Vị trí bàn chân home trong mặt phẳng X-Z
    z_home: float = -0.23

    # Gait parameters
    gait_period: float = 0.80
    duty_factor: float = 0.50
    step_height: float = 0.04
    min_step_length: float = 0.02
    max_step_length: float = 0.08

    # Joint limits, khớp với URDF tối giản hiện tại
    hip_pitch_min: float = -1.57
    hip_pitch_max: float = 1.57
    knee_pitch_min: float = -2.20
    knee_pitch_max: float = 0.20
    hip_yaw_min: float = -0.80
    hip_yaw_max: float = 0.80

    # Watchdog
    cmd_timeout: float = 0.50

    # Control loop
    control_period: float = 0.02

    forward_sign: float = -1.0