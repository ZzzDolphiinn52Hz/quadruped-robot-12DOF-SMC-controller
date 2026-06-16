import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

from quadruped_ros2.robot_config import (
    RobotConfig,
    JOINT_ORDER,
    LEG_EFFORT_INDICES,
    YAW_INDICES,
)
from quadruped_ros2.gait_planner import GaitPlanner
from quadruped_ros2.kinematics import build_joint_command
from quadruped_ros2.joint_state_reader import JointStateReader
from quadruped_ros2.desired_state import DesiredStateEstimator
from quadruped_ros2.smc_math import SMCMath
from quadruped_ros2.hybrid_command import (
    build_smc_leg_effort_command,
    build_yaw_position_command,
)


class QuadrupedMainController(Node):
    def __init__(self):
        super().__init__("quadruped_main_controller")

        self.config = RobotConfig()
        self.gait_planner = GaitPlanner(self.config)
        self.joint_state_reader = JointStateReader()
        self.desired_state = DesiredStateEstimator(joint_count=len(JOINT_ORDER))
        self.smc_math = SMCMath(joint_count=len(JOINT_ORDER))

        self.latest_error = [0.0] * len(JOINT_ORDER)
        self.latest_sliding_surface = [0.0] * len(JOINT_ORDER)
        self.latest_effort_command = [0.0] * len(LEG_EFFORT_INDICES)
        self.latest_stand_fraction = 0.0

        # Lưu torque cũ để giới hạn tốc độ thay đổi torque
        self.previous_effort_command = [0.0] * len(LEG_EFFORT_INDICES)

        self.vx = 0.0
        self.vy = 0.0
        self.wz = 0.0

        self.last_time = self.get_clock().now()
        self.last_cmd_time = self.get_clock().now()
        self.last_log_time = self.get_clock().now()
        self.start_time = self.get_clock().now()
        self.initial_joint_position = None
        self.standup_start_time = None

        # 4 yaw joints: position hold/control
        self.yaw_pub = self.create_publisher(
            Float64MultiArray,
            "/yaw_position_controller/commands",
            10
        )

        # 8 hip/knee pitch joints: SMC effort control
        self.leg_effort_pub = self.create_publisher(
            Float64MultiArray,
            "/leg_effort_controller/commands",
            10
        )

        # Debug: [mode, phase, max_leg_error, max_s, max_effort, max_yaw_error, stand_fraction]
        self.debug_pub = self.create_publisher(
            Float64MultiArray,
            "/smc_debug",
            10
        )
    
        # Debug qd 12 joints
        self.qd_pub = self.create_publisher(
            Float64MultiArray,
            "/desired_joint_command",
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
        self.get_logger().info("Publish: /yaw_position_controller/commands")
        self.get_logger().info("Publish: /leg_effort_controller/commands")
        self.get_logger().info("Publish: /smc_debug")
        self.get_logger().info("Publish: /desired_joint_command")

    def cmd_vel_callback(self, msg):
        self.vx = msg.linear.x
        self.vy = msg.linear.y
        self.wz = msg.angular.z
        self.last_cmd_time = self.get_clock().now()

    def joint_state_callback(self, msg):
        self.joint_state_reader.update(msg)

    def apply_effort_rate_limit(self, effort_command):
        if len(self.previous_effort_command) != len(effort_command):
            self.previous_effort_command = [0.0] * len(effort_command)

        limited_command = []
        max_delta = self.config.effort_rate_limit

        for i, tau in enumerate(effort_command):
            previous_tau = self.previous_effort_command[i]
            delta = tau - previous_tau

            if delta > max_delta:
                tau = previous_tau + max_delta
            elif delta < -max_delta:
                tau = previous_tau - max_delta

            limited_command.append(tau)

        self.previous_effort_command = limited_command.copy()
        return limited_command

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

        # Trong giai đoạn mới khởi động, không cho robot đi ngay.
        # Chỉ cho đứng lên trước.
        if self.standup_start_time is None:
            vx_for_gait = 0.0
            vy_for_gait = 0.0
            wz_for_gait = 0.0
        else:
            standup_elapsed = (now - self.standup_start_time).nanoseconds * 1e-9

            if self.config.full_stand_enabled:
                standup_block_time = (
                    self.config.startup_hold_time
                    + self.config.small_stand_ramp_time
                    + self.config.small_stand_hold_time
                    + self.config.full_stand_ramp_time
                )
            else:
                standup_block_time = float("inf")

            if standup_elapsed < standup_block_time:
                vx_for_gait = 0.0
                vy_for_gait = 0.0
                wz_for_gait = 0.0
            else:
                vx_for_gait = self.vx
                vy_for_gait = self.vy
                wz_for_gait = self.wz

        leg_commands = self.gait_planner.update(
            dt=dt,
            vx=vx_for_gait,
            vy=vy_for_gait,
            wz=wz_for_gait
        )

        joint_command = build_joint_command(
            leg_commands=leg_commands,
            config=self.config
        )

        joint_command, standup_done = self.apply_standup_ramp(
            joint_command=joint_command,
            now=now
        )

        if not self.joint_state_reader.has_state:
            self.publish_debug()
            self.log_status(now)
            return

        qd, dqd, ddqd = self.desired_state.update(
            qd_new=joint_command,
            dt=dt
        )

        # Publish qd để debug
        qd_msg = Float64MultiArray()
        qd_msg.data = qd
        self.qd_pub.publish(qd_msg)

        yaw_msg = Float64MultiArray()
        yaw_msg.data = build_yaw_position_command(qd)
        self.yaw_pub.publish(yaw_msg)

        q = self.joint_state_reader.get_position()
        dq = self.joint_state_reader.get_velocity()

        effort_command, e, de, s = build_smc_leg_effort_command(
            smc_math=self.smc_math,
            qd=qd,
            dqd=dqd,
            ddqd=ddqd,
            q=q,
            dq=dq,
            leg_commands=leg_commands,
            config=self.config,
        )

        self.latest_error = e
        self.latest_sliding_surface = s

        # Ramp torque lúc mới start để tránh giật
        ramp_time = 1.0
        elapsed_from_start = (now - self.start_time).nanoseconds * 1e-9
        torque_scale = min(1.0, elapsed_from_start / ramp_time)
        torque_scale = max(0.45, torque_scale)

        effort_command = [
            torque_scale * tau for tau in effort_command
        ]

        effort_command = self.apply_effort_rate_limit(
            effort_command
        )
        self.latest_effort_command = effort_command.copy()

        effort_msg = Float64MultiArray()
        effort_msg.data = effort_command
        self.leg_effort_pub.publish(effort_msg)

        self.publish_debug()
        self.log_status(now)

    def publish_debug(self):
        max_leg_error = max(
            abs(self.latest_error[i])
            for i in LEG_EFFORT_INDICES
        )
        max_yaw_error = max(
            abs(self.latest_error[i])
            for i in YAW_INDICES
        )
        max_s = max(
            abs(self.latest_sliding_surface[i])
            for i in LEG_EFFORT_INDICES
        )
        max_effort = max(abs(x) for x in self.latest_effort_command)

        msg = Float64MultiArray()
        msg.data = [
            float(self.gait_planner.current_mode),
            float(self.gait_planner.phase),
            float(max_leg_error),
            float(max_s),
            float(max_effort),
            float(max_yaw_error),
            float(self.latest_stand_fraction),
        ]

        self.debug_pub.publish(msg)

    def log_status(self, now):
        elapsed = (now - self.last_log_time).nanoseconds * 1e-9

        if elapsed < 1.0:
            return

        self.last_log_time = now

        max_leg_error = max(
            abs(self.latest_error[i])
            for i in LEG_EFFORT_INDICES
        )
        max_yaw_error = max(
            abs(self.latest_error[i])
            for i in YAW_INDICES
        )
        max_s = max(
            abs(self.latest_sliding_surface[i])
            for i in LEG_EFFORT_INDICES
        )
        max_effort = max(abs(x) for x in self.latest_effort_command)
        max_leg_error_index = max(
            LEG_EFFORT_INDICES,
            key=lambda i: abs(self.latest_error[i])
        )

        self.get_logger().info(
            f"mode={self.gait_planner.current_mode}, "
            f"vx={self.vx:.3f}, vy={self.vy:.3f}, wz={self.wz:.3f}, "
            f"phase={self.gait_planner.phase:.3f}, "
            f"max_leg_error={max_leg_error:.4f}"
            f"({JOINT_ORDER[max_leg_error_index]}), "
            f"max_yaw_error={max_yaw_error:.4f}, "
            f"max_s={max_s:.4f}, max_effort={max_effort:.4f}, "
            f"stand_fraction={self.latest_stand_fraction:.2f}"
        )

    def apply_standup_ramp(self, joint_command, now):
        if not self.joint_state_reader.has_state:
            return joint_command, False

        q_now = self.joint_state_reader.get_position()

        if self.initial_joint_position is None:
            self.initial_joint_position = q_now.copy()
            self.standup_start_time = now
            self.start_time = now
            self.previous_effort_command = [0.0] * len(LEG_EFFORT_INDICES)
            self.latest_effort_command = [0.0] * len(LEG_EFFORT_INDICES)
            self.latest_stand_fraction = 0.0
            self.desired_state.reset(self.initial_joint_position)
            self.get_logger().info(
                "Captured initial joint state; holding current pose before standup."
            )

        elapsed = (now - self.standup_start_time).nanoseconds * 1e-9

        if elapsed < self.config.startup_hold_time:
            self.latest_stand_fraction = 0.0
            return self.initial_joint_position.copy(), False

        ramp_elapsed = elapsed - self.config.startup_hold_time

        if ramp_elapsed < self.config.small_stand_ramp_time:
            alpha = ramp_elapsed / self.config.small_stand_ramp_time
            alpha = alpha * alpha * (3.0 - 2.0 * alpha)
            stand_fraction = self.config.small_stand_fraction * alpha
        elif not self.config.full_stand_enabled:
            stand_fraction = self.config.small_stand_fraction
        elif ramp_elapsed < (
            self.config.small_stand_ramp_time
            + self.config.small_stand_hold_time
        ):
            stand_fraction = self.config.small_stand_fraction
        else:
            full_ramp_elapsed = (
                ramp_elapsed
                - self.config.small_stand_ramp_time
                - self.config.small_stand_hold_time
            )
            alpha = min(1.0, full_ramp_elapsed / self.config.full_stand_ramp_time)
            alpha = alpha * alpha * (3.0 - 2.0 * alpha)
            stand_fraction = (
                self.config.small_stand_fraction
                + (1.0 - self.config.small_stand_fraction) * alpha
            )

        stand_fraction = max(0.0, min(1.0, stand_fraction))
        self.latest_stand_fraction = stand_fraction

        blended_command = [
            (
                (1.0 - stand_fraction) * self.initial_joint_position[i]
                + stand_fraction * joint_command[i]
            )
            for i in range(len(joint_command))
        ]

        standup_done = stand_fraction >= 1.0

        return blended_command, standup_done


def main(args=None):
    rclpy.init(args=args)

    node = QuadrupedMainController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()

    if rclpy.ok():
        rclpy.shutdown()

if __name__ == "__main__":
    main()
