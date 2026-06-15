import math

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from std_msgs.msg import Float64MultiArray


class QuadrupedGaitController(Node):
    def __init__(self):
        super().__init__('gait_controller')

        # Publisher gửi 12 góc joint tới webots_ros2_control
        self.joint_pub = self.create_publisher(
            Float64MultiArray,
            '/position_controller/commands',
            10
        )

        # Subscriber nhận lệnh vận tốc
        self.cmd_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )

        # Thông số chân, giống mô hình cũ của bạn
        self.L1 = 0.16
        self.L2 = 0.16

        # Pose đứng cơ bản
        self.stand_hip = 0.70
        self.stand_knee = -1.40

        # Thông số gait
        self.z_home = -0.23       # vị trí bàn chân theo phương đứng, âm là xuống dưới
        self.step_height = 0.04   # độ nhấc chân
        self.max_step_length = 0.08
        self.min_step_length = 0.02
        self.gait_period = 0.80   # chu kỳ bước, giây

        # Lệnh vận tốc hiện tại
        self.vx = 0.0
        self.vy = 0.0
        self.wz = 0.0

        self.phase = 0.0
        self.last_time = self.get_clock().now()
        self.last_cmd_time = self.get_clock().now()

        # 50 Hz
        self.timer = self.create_timer(0.02, self.control_loop)

        self.get_logger().info('Quadruped gait controller started.')
        self.get_logger().info('Subscribe: /cmd_vel')
        self.get_logger().info('Publish: /position_controller/commands')

    def cmd_vel_callback(self, msg):
        self.vx = msg.linear.x
        self.vy = msg.linear.y
        self.wz = msg.angular.z
        self.last_cmd_time = self.get_clock().now()

    def clamp(self, value, min_value, max_value):
        return max(min_value, min(max_value, value))

    def inverse_kinematics_2link(self, x, z):
        """
        IK cho 1 chân 2-link trong mặt phẳng X-Z.
        Kết quả trả về:
        q1 = hip_pitch
        q2 = knee_pitch
        """

        D = (x * x + z * z - self.L1 * self.L1 - self.L2 * self.L2) / (2.0 * self.L1 * self.L2)
        D = self.clamp(D, -0.999, 0.999)

        q2 = -math.acos(D)

        q1 = math.atan2(x, -z) - math.atan2(
            self.L2 * math.sin(q2),
            self.L1 + self.L2 * math.cos(q2)
        )

        # Giới hạn giống URDF
        q1 = self.clamp(q1, -1.57, 1.57)
        q2 = self.clamp(q2, -2.20, 0.20)

        return q1, q2

    def get_leg_trajectory(self, leg_phase, step_length, direction):
        """
        Tạo quỹ đạo bàn chân đơn giản:
        - 0.0 -> 0.5: stance phase, chân quét về sau
        - 0.5 -> 1.0: swing phase, chân nhấc lên và đưa ra trước
        """

        leg_phase = leg_phase % 1.0

        if leg_phase < 0.5:
            # Stance: chân ở mặt đất, đi từ trước về sau
            u = leg_phase / 0.5
            x = direction * (step_length / 2.0 - step_length * u)
            z = self.z_home
        else:
            # Swing: chân nhấc lên, đi từ sau ra trước
            u = (leg_phase - 0.5) / 0.5
            x = direction * (-step_length / 2.0 + step_length * u)
            z = self.z_home + self.step_height * math.sin(math.pi * u)

        return x, z

    def stand_command(self):
        """
        Thứ tự phải giống config/ros2_controllers.yaml:
        FL_yaw, FL_hip, FL_knee,
        FR_yaw, FR_hip, FR_knee,
        RL_yaw, RL_hip, RL_knee,
        RR_yaw, RR_hip, RR_knee
        """
        return [
            0.0, self.stand_hip, self.stand_knee,
            0.0, self.stand_hip, self.stand_knee,
            0.0, self.stand_hip, self.stand_knee,
            0.0, self.stand_hip, self.stand_knee,
        ]

    def control_loop(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds * 1e-9
        self.last_time = now

        if dt <= 0.0:
            return

        # Watchdog: nếu quá 0.5s không có /cmd_vel thì đứng yên
        time_since_cmd = (now - self.last_cmd_time).nanoseconds * 1e-9
        if time_since_cmd > 0.5:
            self.vx = 0.0
            self.vy = 0.0
            self.wz = 0.0

        speed = abs(self.vx)

        # Nếu vận tốc nhỏ thì giữ đứng
        if speed < 0.02:
            joint_cmd = self.stand_command()
            self.publish_joint_command(joint_cmd)
            return

        # Cập nhật phase gait
        self.phase += dt / self.gait_period
        self.phase = self.phase % 1.0

        direction = 1.0 if self.vx >= 0.0 else -1.0

        step_length = self.clamp(
            speed * 0.35,
            self.min_step_length,
            self.max_step_length
        )

        # Trot gait:
        # FL + RR cùng pha
        # FR + RL lệch pha 0.5
        phase_FL = self.phase
        phase_RR = self.phase
        phase_FR = self.phase + 0.5
        phase_RL = self.phase + 0.5

        x_FL, z_FL = self.get_leg_trajectory(phase_FL, step_length, direction)
        x_FR, z_FR = self.get_leg_trajectory(phase_FR, step_length, direction)
        x_RL, z_RL = self.get_leg_trajectory(phase_RL, step_length, direction)
        x_RR, z_RR = self.get_leg_trajectory(phase_RR, step_length, direction)

        FL_hip, FL_knee = self.inverse_kinematics_2link(x_FL, z_FL)
        FR_hip, FR_knee = self.inverse_kinematics_2link(x_FR, z_FR)
        RL_hip, RL_knee = self.inverse_kinematics_2link(x_RL, z_RL)
        RR_hip, RR_knee = self.inverse_kinematics_2link(x_RR, z_RR)

        # Yaw tạm thời giữ 0.
        # Sau này ta mới thêm crab walk / spin bằng hip_yaw.
        FL_yaw = 0.0
        FR_yaw = 0.0
        RL_yaw = 0.0
        RR_yaw = 0.0

        joint_cmd = [
            FL_yaw, FL_hip, FL_knee,
            FR_yaw, FR_hip, FR_knee,
            RL_yaw, RL_hip, RL_knee,
            RR_yaw, RR_hip, RR_knee,
        ]

        self.publish_joint_command(joint_cmd)

    def publish_joint_command(self, joint_cmd):
        msg = Float64MultiArray()
        msg.data = joint_cmd
        self.joint_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    node = QuadrupedGaitController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()