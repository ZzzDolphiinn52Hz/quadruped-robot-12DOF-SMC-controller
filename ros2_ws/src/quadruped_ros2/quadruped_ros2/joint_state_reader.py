from quadruped_ros2.robot_config import JOINT_ORDER


class JointStateReader:
    def __init__(self):
        self.q = [0.0] * len(JOINT_ORDER)
        self.dq = [0.0] * len(JOINT_ORDER)
        self.has_state = False

        self.name_to_index = {
            name: index for index, name in enumerate(JOINT_ORDER)
        }

    def update(self, msg):
        """
        /joint_states có thể trả joint không đúng thứ tự.
        Hàm này sắp xếp lại theo đúng JOINT_ORDER.
        """

        for i, name in enumerate(msg.name):
            if name not in self.name_to_index:
                continue

            target_index = self.name_to_index[name]

            if i < len(msg.position):
                self.q[target_index] = msg.position[i]

            if i < len(msg.velocity):
                self.dq[target_index] = msg.velocity[i]

        self.has_state = True

    def get_position(self):
        return self.q.copy()

    def get_velocity(self):
        return self.dq.copy()