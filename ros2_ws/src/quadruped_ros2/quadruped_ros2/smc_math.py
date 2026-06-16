class SMCMath:
    def __init__(self, joint_count, lambda_gain=50.0):
        self.joint_count = joint_count
        self.lambda_gain = lambda_gain

    def compute_error(self, qd, q):
        return [
            qd[i] - q[i]
            for i in range(self.joint_count)
        ]

    def compute_velocity_error(self, dqd, dq):
        return [
            dqd[i] - dq[i]
            for i in range(self.joint_count)
        ]

    def compute_sliding_surface(self, qd, dqd, q, dq):
        """
        s = (dqd - dq) + lambda * (qd - q)
        """
        e = self.compute_error(qd, q)
        de = self.compute_velocity_error(dqd, dq)

        s = [
            de[i] + self.lambda_gain * e[i]
            for i in range(self.joint_count)
        ]

        return e, de, s

    @staticmethod
    def clamp(value, min_value, max_value):
        return max(min_value, min(max_value, value))

    @classmethod
    def saturate(cls, value, boundary_layer):
        if boundary_layer <= 0.0:
            if value > 0.0:
                return 1.0
            if value < 0.0:
                return -1.0
            return 0.0

        return cls.clamp(value / boundary_layer, -1.0, 1.0)

    def compute_limited_sliding_surface(
        self,
        qd,
        dqd,
        q,
        dq,
        lambda_gains,
        position_error_limit,
        velocity_error_limit,
    ):
        e = []
        de = []
        s = []

        for i in range(self.joint_count):
            position_error = self.clamp(
                qd[i] - q[i],
                -position_error_limit,
                position_error_limit,
            )
            velocity_error = self.clamp(
                dqd[i] - dq[i],
                -velocity_error_limit,
                velocity_error_limit,
            )

            e.append(position_error)
            de.append(velocity_error)
            s.append(velocity_error + lambda_gains[i] * position_error)

        return e, de, s

    def compute_effort(
        self,
        qd,
        dqd,
        ddqd,
        q,
        dq,
        lambda_gains,
        linear_gains,
        switching_gains,
        inertia,
        effort_limits,
        position_error_limit,
        velocity_error_limit,
        desired_acceleration_limit,
        boundary_layer,
        effort_signs,
        support_torque=None,
    ):
        e, de, s = self.compute_limited_sliding_surface(
            qd=qd,
            dqd=dqd,
            q=q,
            dq=dq,
            lambda_gains=lambda_gains,
            position_error_limit=position_error_limit,
            velocity_error_limit=velocity_error_limit,
        )

        if support_torque is None:
            support_torque = [0.0] * self.joint_count

        efforts = []

        for i in range(self.joint_count):
            desired_acceleration = self.clamp(
                ddqd[i],
                -desired_acceleration_limit,
                desired_acceleration_limit,
            )

            equivalent = inertia[i] * desired_acceleration
            reaching = linear_gains[i] * s[i]
            switching = switching_gains[i] * self.saturate(
                s[i],
                boundary_layer,
            )

            tau = equivalent + reaching + switching + support_torque[i]
            tau = effort_signs[i] * tau
            tau = self.clamp(tau, -effort_limits[i], effort_limits[i])

            efforts.append(tau)

        return efforts, e, de, s
