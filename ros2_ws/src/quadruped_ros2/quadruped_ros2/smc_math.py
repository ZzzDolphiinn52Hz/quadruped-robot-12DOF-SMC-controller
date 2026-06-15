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