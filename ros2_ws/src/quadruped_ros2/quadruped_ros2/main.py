import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

from quadruped_ros2.robot_config import RobotConfig, JOINT_ORDER
from quadruped_ros2.gait_planner import GaitPlanner
from quadruped_ros2.kinematics import build_joint_command
from quadruped_ros2.joint_state_reader import JointStateReader
from quadruped_ros2.desired_state import DesiredStateEstimator
from quadruped_ros2.smc_math import SMCMath


class QuadrupedMainController(Node):
    def __init__(self):
        super().__init__("quadruped_main_controller")

        self.config = RobotConfig()
        self.gait_planner = GaitPlanner(self.config)
        self.joint_state_reader = JointStateReader()
        self.desired_state = DesiredStateEstimator(joint_count=len(JOINT_ORDER))
        self.smc_math = SMCMath(joint_count=len(JOINT_ORDER), lambda_gain=50.0)

        self.latest_error = [0.0] * len(JOINT_ORDER)
        self.latest_sliding_surface = [0.0] * len(JOINT_ORDER)

        self.vx = 0.0
        self.vy = 0.0
        self.wz = 0.0

        self.last_time = self.get_clock().now()
        self.last_cmd_time = self.get_clock().now()
        self.last_log_time = self.get_clock().now()

        self.joint_pub = self.create_publisher(
            Float64MultiArray,
            "/position_controller/commands",
            10
        )

        self.debug_pub = self.create_publisher(
            Float64MultiArray,
            "/smc_debug",
            10
        )

        self.cmd_sub = self.create_subscription(
            Twist,
            "/cmd_vel",
            self.cmd_vel_callback,
            10
        )

        self.joint_state_sub = self.create_subscription(
            JointState,
            "/joint_states",
            self.joint_state_callback,
            10
        )

        self.timer = self.create_timer(
            self.config.control_period,
            self.control_loop
        )

        self.get_logger().info("Quadruped main controller started.")
        self.get_logger().info("Subscribe: /cmd_vel")
        self.get_logger().info("Publish: /position_controller/commands")

    def cmd_vel_callback(self, msg):
        self.vx = msg.linear.x
        self.vy = msg.linear.y
        self.wz = msg.angular.z
        self.last_cmd_time = self.get_clock().now()

    def control_loop(self):
        now = self.get_clock().now()

        dt = (now - self.last_time).nanoseconds * 1e-9
        self.last_time = now

        if dt <= 0.0:
            return

        time_since_cmd = (now - self.last_cmd_time).nanoseconds * 1e-9

        if time_since_cmd > self.config.cmd_timeout:
            self.vx = 0.0
            self.vy = 0.0
            self.wz = 0.0

        leg_commands = self.gait_planner.update(
            dt=dt,
            vx=self.vx,
            vy=self.vy,
            wz=self.wz
        )

        joint_command = build_joint_command(
            leg_commands=leg_commands,
            config=self.config
        )

        qd, dqd, ddqd = self.desired_state.update(
            qd_new=joint_command,
            dt=dt
        )

        if self.joint_state_reader.has_state:
            q = self.joint_state_reader.get_position()
            dq = self.joint_state_reader.get_velocity()

            e, de, s = self.smc_math.compute_sliding_surface(
                qd=qd,
                dqd=dqd,
                q=q,
                dq=dq
            )

            self.latest_error = e
            self.latest_sliding_surface = s

        msg = Float64MultiArray()
        msg.data = joint_command
        self.joint_pub.publish(msg)

        self.publish_debug()

        self.log_status(now)

    def log_status(self, now):
        elapsed = (now - self.last_log_time).nanoseconds * 1e-9

        if elapsed < 1.0:
            return

        self.last_log_time = now

        max_error = max(abs(x) for x in self.latest_error)
        max_s = max(abs(x) for x in self.latest_sliding_surface)

        self.get_logger().info(
            f"mode={self.gait_planner.current_mode}, "
            f"vx={self.vx:.2f}, vy={self.vy:.2f}, wz={self.wz:.2f}, "
            f"phase={self.gait_planner.phase:.2f}, "
            f"max_error={max_error:.4f}, max_s={max_s:.4f}"
        )
    
    def joint_state_callback(self, msg):
        self.joint_state_reader.update(msg)

    def publish_debug(self):
        max_error = max(abs(x) for x in self.latest_error)
        max_s = max(abs(x) for x in self.latest_sliding_surface)

        msg = Float64MultiArray()
        msg.data = [
            float(self.gait_planner.current_mode),
            float(self.gait_planner.phase),
            float(max_error),
            float(max_s),
        ]

        self.debug_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    node = QuadrupedMainController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()