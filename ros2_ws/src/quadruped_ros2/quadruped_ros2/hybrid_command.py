import math

from quadruped_ros2.robot_config import (
    JOINT_ORDER,
    YAW_INDICES,
    LEG_EFFORT_INDICES,
    HIP_PITCH_INDICES,
    KNEE_PITCH_INDICES,
)


LEG_JOINT_INDICES = {
    "FL": (0, 1, 2),
    "FR": (3, 4, 5),
    "RL": (6, 7, 8),
    "RR": (9, 10, 11),
}


def get_leg_name_from_joint_index(idx):
    if idx in [0, 1, 2]:
        return "FL"
    if idx in [3, 4, 5]:
        return "FR"
    if idx in [6, 7, 8]:
        return "RL"
    if idx in [9, 10, 11]:
        return "RR"
    return None


def build_yaw_position_command(qd):
    return [qd[i] for i in YAW_INDICES]


def build_joint_type_values(yaw_value, hip_value, knee_value):
    values = []

    for idx in range(len(JOINT_ORDER)):
        if idx in YAW_INDICES:
            values.append(yaw_value)
        elif idx in HIP_PITCH_INDICES:
            values.append(hip_value)
        elif idx in KNEE_PITCH_INDICES:
            values.append(knee_value)
        else:
            values.append(0.0)

    return values


def build_effort_limits(config):
    limits = []

    for idx in range(len(JOINT_ORDER)):
        if idx in YAW_INDICES:
            limits.append(config.yaw_effort_limit)
        else:
            limits.append(config.effort_limit)

    return limits


def build_support_torque(leg_commands, config, q):
    support = [0.0] * len(JOINT_ORDER)

    if not config.use_support_torque:
        return support

    contact_count = sum(
        1 for leg_name in LEG_JOINT_INDICES
        if leg_commands[leg_name]["contact"]
    )
    contact_count = max(1, contact_count)
    body_force = (
        config.support_force_scale
        * config.body_mass
        * config.gravity
        / contact_count
    )

    thigh_com = 0.5 * config.L1
    shank_com = 0.5 * config.L2

    for leg_name, (_, hip_idx, knee_idx) in LEG_JOINT_INDICES.items():
        q1 = q[hip_idx]
        q2 = q[knee_idx]
        contact_scale = 1.0 if leg_commands[leg_name]["contact"] else 0.0

        gravity_hip = (
            config.thigh_mass * config.gravity * thigh_com * math.sin(q1)
            + config.shank_mass * config.gravity * (
                config.L1 * math.sin(q1)
                + shank_com * math.sin(q1 + q2)
            )
        )
        gravity_knee = (
            config.shank_mass
            * config.gravity
            * shank_com
            * math.sin(q1 + q2)
        )

        load_hip = (
            contact_scale
            * body_force
            * (
                config.L1 * math.sin(q1)
                + config.L2 * math.sin(q1 + q2)
            )
        )
        load_knee = (
            contact_scale
            * body_force
            * config.L2
            * math.sin(q1 + q2)
        )

        support[hip_idx] = gravity_hip + load_hip + config.hip_support_torque
        support[knee_idx] = gravity_knee + load_knee + config.knee_support_torque

    return support


def build_smc_effort_command(
    smc_math,
    qd,
    dqd,
    ddqd,
    q,
    dq,
    leg_commands,
    config,
):
    lambda_gains = build_joint_type_values(
        config.smc_lambda_yaw,
        config.smc_lambda_hip,
        config.smc_lambda_knee,
    )
    linear_gains = build_joint_type_values(
        config.smc_linear_gain_yaw,
        config.smc_linear_gain_hip,
        config.smc_linear_gain_knee,
    )
    switching_gains = build_joint_type_values(
        config.smc_switching_gain_yaw,
        config.smc_switching_gain_hip,
        config.smc_switching_gain_knee,
    )
    inertia = build_joint_type_values(
        config.smc_inertia_yaw,
        config.smc_inertia_hip,
        config.smc_inertia_knee,
    )
    effort_signs = build_joint_type_values(
        config.yaw_effort_sign,
        config.hip_effort_sign,
        config.knee_effort_sign,
    )

    return smc_math.compute_effort(
        qd=qd,
        dqd=dqd,
        ddqd=ddqd,
        q=q,
        dq=dq,
        lambda_gains=lambda_gains,
        linear_gains=linear_gains,
        switching_gains=switching_gains,
        inertia=inertia,
        effort_limits=build_effort_limits(config),
        position_error_limit=config.position_error_limit,
        velocity_error_limit=config.velocity_error_limit,
        desired_acceleration_limit=config.desired_acceleration_limit,
        boundary_layer=config.smc_boundary_layer,
        effort_signs=effort_signs,
        support_torque=build_support_torque(leg_commands, config, q),
    )


def build_smc_leg_effort_command(
    smc_math,
    qd,
    dqd,
    ddqd,
    q,
    dq,
    leg_commands,
    config,
):
    effort_command, e, de, s = build_smc_effort_command(
        smc_math=smc_math,
        qd=qd,
        dqd=dqd,
        ddqd=ddqd,
        q=q,
        dq=dq,
        leg_commands=leg_commands,
        config=config,
    )

    leg_effort_command = [
        effort_command[i]
        for i in LEG_EFFORT_INDICES
    ]

    return leg_effort_command, e, de, s
