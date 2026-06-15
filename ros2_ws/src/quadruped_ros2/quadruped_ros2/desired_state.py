class DesiredStateEstimator:
    def __init__(self, joint_count):
        self.joint_count = joint_count

        self.qd_prev = [0.0] * joint_count
        self.dqd_prev = [0.0] * joint_count

        self.qd = [0.0] * joint_count
        self.dqd = [0.0] * joint_count
        self.ddqd = [0.0] * joint_count

        self.initialized = False

    def update(self, qd_new, dt):
        if dt <= 0.0:
            return self.qd, self.dqd, self.ddqd

        if not self.initialized:
            self.qd = qd_new.copy()
            self.qd_prev = qd_new.copy()

            self.dqd = [0.0] * self.joint_count
            self.dqd_prev = [0.0] * self.joint_count
            self.ddqd = [0.0] * self.joint_count

            self.initialized = True

            return self.qd, self.dqd, self.ddqd

        self.qd = qd_new.copy()

        self.dqd = [
            (self.qd[i] - self.qd_prev[i]) / dt
            for i in range(self.joint_count)
        ]

        self.ddqd = [
            (self.dqd[i] - self.dqd_prev[i]) / dt
            for i in range(self.joint_count)
        ]

        self.qd_prev = self.qd.copy()
        self.dqd_prev = self.dqd.copy()

        return self.qd, self.dqd, self.ddqd