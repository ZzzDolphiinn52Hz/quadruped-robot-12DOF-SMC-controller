from quadruped_ros2.robot_config import (
    YAW_INDICES,
    LEG_EFFORT_INDICES,
)


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def build_yaw_position_command(qd):
    """
    Lấy 4 joint yaw từ vector qd 12 joint.
    Thứ tự:
    FL_hip_yaw, FR_hip_yaw, RL_hip_yaw, RR_hip_yaw
    """
    return [qd[i] for i in YAW_INDICES]


def build_leg_effort_command(qd, dqd, q, dq, config):
    """
    Temporary PD effort controller cho 8 joint pitch/knee.

    Output thứ tự:
    FL_hip_pitch, FL_knee_pitch,
    FR_hip_pitch, FR_knee_pitch,
    RL_hip_pitch, RL_knee_pitch,
    RR_hip_pitch, RR_knee_pitch
    """

    efforts = []

    for idx in LEG_EFFORT_INDICES:
        name_type = "hip" if idx in [1, 4, 7, 10] else "knee"

        if name_type == "hip":
            kp = config.kp_hip
            kd = config.kd_hip
        else:
            kp = config.kp_knee
            kd = config.kd_knee

        position_error = qd[idx] - q[idx]
        velocity_error = dqd[idx] - dq[idx]

        position_error = clamp(
            position_error,
            -config.position_error_limit,
            config.position_error_limit
        )

        velocity_error = clamp(
            velocity_error,
            -config.velocity_error_limit,
            config.velocity_error_limit
        )

        tau = kp * position_error + kd * velocity_error

        # Bù lực giữ thân robot
        if name_type == "hip":
            tau += config.hip_support_torque
        else:
            tau += config.knee_support_torque

        tau = config.effort_sign * tau
        tau = clamp(tau, -config.effort_limit, config.effort_limit)

        efforts.append(tau)

    return efforts