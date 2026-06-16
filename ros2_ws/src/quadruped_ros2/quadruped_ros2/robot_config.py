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

HIP_PITCH_INDICES = [1, 4, 7, 10]
KNEE_PITCH_INDICES = [2, 5, 8, 11]


@dataclass
class RobotConfig:
    # Link length
    L1: float = 0.16
    L2: float = 0.16

    # Vị trí bàn chân home
    z_home: float = -0.22

    # Gait parameters
    gait_period: float = 1.60
    duty_factor: float = 0.78
    step_height: float = 0.008
    min_step_length: float = 0.006
    max_step_length: float = 0.018
    step_length_gain: float = 0.80

    # Joint limits
    hip_pitch_min: float = -1.57
    hip_pitch_max: float = 1.57
    knee_pitch_min: float = -2.20
    knee_pitch_max: float = 0.20
    hip_yaw_min: float = -0.80
    hip_yaw_max: float = 0.80

    # Watchdog
    cmd_timeout: float = 0.50
    
    startup_hold_time: float = 1.5
    small_stand_fraction: float = 0.05
    small_stand_ramp_time: float = 4.0
    small_stand_hold_time: float = 8.0
    full_stand_enabled: bool = False
    full_stand_ramp_time: float = 10.0

    # Control loop
    control_period: float = 0.02

    # Đảo chiều tiến/lùi cho đúng Webots model
    forward_sign: float = -1.0

    # Sliding Mode Controller for hip/knee effort tracking
    smc_lambda_yaw: float = 1.5
    smc_lambda_hip: float = 3.0
    smc_lambda_knee: float = 2.0

    smc_linear_gain_yaw: float = 0.06
    smc_linear_gain_hip: float = 0.25
    smc_linear_gain_knee: float = 0.30

    smc_switching_gain_yaw: float = 0.12
    smc_switching_gain_hip: float = 0.90
    smc_switching_gain_knee: float = 1.10

    # Boundary layer width for sat(s / phi). Increase to reduce chattering.
    smc_boundary_layer: float = 0.35

    # Small desired acceleration feed-forward. Keep conservative without a
    # full rigid-body dynamics model.
    smc_inertia_yaw: float = 0.004
    smc_inertia_hip: float = 0.010
    smc_inertia_knee: float = 0.008

    # Giới hạn torque
    effort_limit: float = 3.80
    effort_rate_limit: float = 0.140
    yaw_effort_limit: float = 0.45

    # Giới hạn error để tránh torque spike
    position_error_limit: float = 0.70
    velocity_error_limit: float = 2.50
    desired_acceleration_limit: float = 25.0

    # Torque hỗ trợ giữ thân trong stance. Keep disabled while tuning the
    # small first stand pose.
    use_support_torque: bool = False
    hip_support_torque: float = 0.12
    knee_support_torque: float = 0.45

    # Nếu joint chạy ngược chiều qd, đổi riêng sign của nhóm joint đó.
    yaw_effort_sign: float = 1.0
    hip_effort_sign: float = 1.0
    knee_effort_sign: float = 1.0
