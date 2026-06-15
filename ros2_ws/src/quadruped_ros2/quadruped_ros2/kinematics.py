import math

from quadruped_ros2.bezier_utils import clamp


def inverse_kinematics_2link(x, z, config):
    """
    IK cho chân 2-link trong mặt phẳng X-Z.
    Công thức bám theo SMC_12DOF.c cũ.

    Input:
        x: vị trí bàn chân theo phương tiến/lùi
        z: vị trí bàn chân theo phương đứng, âm là xuống dưới

    Output:
        q1: hip_pitch
        q2: knee_pitch
    """

    L1 = config.L1
    L2 = config.L2

    D = (x * x + z * z - L1 * L1 - L2 * L2) / (2.0 * L1 * L2)
    D = clamp(D, -0.999, 0.999)

    q2 = -math.acos(D)

    q1 = math.atan2(x, -z) - math.atan2(
        L2 * math.sin(q2),
        L1 + L2 * math.cos(q2)
    )

    q1 = clamp(q1, config.hip_pitch_min, config.hip_pitch_max)
    q2 = clamp(q2, config.knee_pitch_min, config.knee_pitch_max)

    return q1, q2


def build_joint_command(leg_commands, config):
    """
    Trả về vector 12 joint theo đúng thứ tự trong ros2_controllers.yaml:

    FL_yaw, FL_hip, FL_knee,
    FR_yaw, FR_hip, FR_knee,
    RL_yaw, RL_hip, RL_knee,
    RR_yaw, RR_hip, RR_knee
    """

    command = []

    for leg in ["FL", "FR", "RL", "RR"]:
        yaw = leg_commands[leg]["yaw"]
        x = leg_commands[leg]["x"]
        z = leg_commands[leg]["z"]

        hip, knee = inverse_kinematics_2link(x, z, config)

        yaw = clamp(yaw, config.hip_yaw_min, config.hip_yaw_max)

        command.extend([yaw, hip, knee])

    return command