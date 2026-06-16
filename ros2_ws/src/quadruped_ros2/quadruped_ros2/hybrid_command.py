from quadruped_ros2.robot_config import (
    JOINT_ORDER,
    YAW_INDICES,
    LEG_EFFORT_INDICES,
    HIP_PITCH_INDICES,
    KNEE_PITCH_INDICES,
)


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


def build_support_torque(leg_commands, config):
    support = [0.0] * len(JOINT_ORDER)

    if not config.use_support_torque:
        return support

    for idx in LEG_EFFORT_INDICES:
        leg_name = get_leg_name_from_joint_index(idx)
        contact = leg_commands[leg_name]["contact"]

        if idx in HIP_PITCH_INDICES:
            support_torque = config.hip_support_torque
        else:
            support_torque = config.knee_support_torque

        if not contact:
            support_torque *= 0.10

        support[idx] = support_torque

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
        support_torque=build_support_torque(leg_commands, config),
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
