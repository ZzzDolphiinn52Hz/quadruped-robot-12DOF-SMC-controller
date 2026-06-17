import csv
import math
import os
from collections import deque
from datetime import datetime

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

from quadruped_ros2.robot_config import JOINT_ORDER, LEG_EFFORT_INDICES


DEBUG_NAMES = [
    "mode",
    "phase",
    "max_leg_error",
    "max_s",
    "max_effort",
    "max_yaw_error",
    "stand_fraction",
    "cmd_vx",
    "cmd_vy",
    "cmd_wz",
    "cmd_age",
]


class JointPlotter(Node):
    def __init__(self):
        super().__init__("joint_plotter")

        self.declare_parameter("joints", JOINT_ORDER)
        self.declare_parameter("output_dir", "~/quadruped_joint_logs")
        self.declare_parameter("live_plot", True)
        self.declare_parameter("save_csv", True)
        self.declare_parameter("save_plot_on_exit", True)
        self.declare_parameter("plot_window_sec", 10.0)
        self.declare_parameter("plot_period", 0.20)

        requested_joints = list(self.get_parameter("joints").value)
        self.selected_joints = [
            name for name in requested_joints
            if name in JOINT_ORDER
        ]
        if not self.selected_joints:
            self.selected_joints = JOINT_ORDER.copy()

        self.output_dir = os.path.expanduser(
            self.get_parameter("output_dir").value
        )
        self.live_plot = bool(self.get_parameter("live_plot").value)
        self.save_csv = bool(self.get_parameter("save_csv").value)
        self.save_plot_on_exit = bool(
            self.get_parameter("save_plot_on_exit").value
        )
        self.plot_window_sec = float(
            self.get_parameter("plot_window_sec").value
        )
        plot_period = float(self.get_parameter("plot_period").value)

        os.makedirs(self.output_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path = os.path.join(
            self.output_dir,
            f"joint_angles_{stamp}.csv",
        )
        self.plot_path = os.path.join(
            self.output_dir,
            f"joint_angles_{stamp}.png",
        )

        self.name_to_index = {
            name: index for index, name in enumerate(JOINT_ORDER)
        }

        self.t0 = None
        self.latest_desired = [math.nan] * len(JOINT_ORDER)
        self.latest_effort = [math.nan] * len(JOINT_ORDER)
        self.latest_debug = [math.nan] * len(DEBUG_NAMES)

        self.time_history = deque()
        self.actual_history = {
            name: deque() for name in self.selected_joints
        }
        self.desired_history = {
            name: deque() for name in self.selected_joints
        }

        self.csv_file = None
        self.csv_writer = None
        self._open_csv()

        self.figure = None
        self.axes = []
        self.lines = {}
        self.plt = None
        self._init_plot()

        self.joint_sub = self.create_subscription(
            JointState,
            "/joint_states",
            self.joint_callback,
            50,
        )
        self.desired_sub = self.create_subscription(
            Float64MultiArray,
            "/desired_joint_command",
            self.desired_callback,
            10,
        )
        self.debug_sub = self.create_subscription(
            Float64MultiArray,
            "/smc_debug",
            self.debug_callback,
            10,
        )
        self.effort_sub = self.create_subscription(
            Float64MultiArray,
            "/leg_effort_controller/commands",
            self.effort_callback,
            10,
        )
        self.plot_timer = self.create_timer(
            max(0.05, plot_period),
            self.update_plot,
        )

        self.get_logger().info("Joint plotter started.")
        self.get_logger().info("Listening: /joint_states")
        self.get_logger().info("Listening: /desired_joint_command")
        self.get_logger().info("Listening: /leg_effort_controller/commands")
        self.get_logger().info("Listening: /smc_debug")
        if self.save_csv:
            self.get_logger().info(f"CSV: {self.csv_path}")
        if self.live_plot or self.save_plot_on_exit:
            self.get_logger().info(f"Plot image on exit: {self.plot_path}")

    def _open_csv(self):
        if not self.save_csv:
            return

        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)

        header = ["time_sec"]
        for joint_name in JOINT_ORDER:
            header.extend([
                f"{joint_name}_pos",
                f"{joint_name}_vel",
                f"{joint_name}_desired",
                f"{joint_name}_error",
                f"{joint_name}_effort",
            ])
        header.extend(DEBUG_NAMES)
        self.csv_writer.writerow(header)

    def _init_plot(self):
        if not (self.live_plot or self.save_plot_on_exit):
            return

        try:
            import matplotlib.pyplot as plt
        except ImportError:
            self.get_logger().warning(
                "matplotlib is not installed; CSV logging will still work."
            )
            self.live_plot = False
            self.save_plot_on_exit = False
            return

        self.plt = plt
        if self.live_plot:
            plt.ion()

        cols = 3
        rows = math.ceil(len(self.selected_joints) / cols)
        self.figure, axes = plt.subplots(
            rows,
            cols,
            figsize=(13, max(7, rows * 2.3)),
            sharex=True,
        )

        if not isinstance(axes, (list, tuple)):
            axes = axes.flatten()
        self.axes = list(axes)

        for ax in self.axes[len(self.selected_joints):]:
            ax.set_visible(False)

        for ax, joint_name in zip(self.axes, self.selected_joints):
            actual_line, = ax.plot([], [], label="actual", linewidth=1.3)
            desired_line, = ax.plot(
                [], [], label="desired", linewidth=1.0, linestyle="--"
            )
            ax.set_title(joint_name, fontsize=9)
            ax.set_ylabel("rad")
            ax.set_ylim(-2, 2)
            ax.grid(True, alpha=0.35)
            ax.legend(loc="upper right", fontsize=7)
            self.lines[joint_name] = (actual_line, desired_line)

        for ax in self.axes[-cols:]:
            if ax.get_visible():
                ax.set_xlabel("time [s]")

        self.figure.suptitle("Quadruped joint angles")
        self.figure.tight_layout()

        if self.live_plot:
            plt.show(block=False)

    def _message_time(self, msg):
        stamp = msg.header.stamp
        if stamp.sec == 0 and stamp.nanosec == 0:
            now = self.get_clock().now()
            return now.nanoseconds * 1e-9
        return float(stamp.sec) + float(stamp.nanosec) * 1e-9

    def desired_callback(self, msg):
        count = min(len(msg.data), len(JOINT_ORDER))
        for i in range(count):
            self.latest_desired[i] = float(msg.data[i])

    def debug_callback(self, msg):
        count = min(len(msg.data), len(DEBUG_NAMES))
        for i in range(count):
            self.latest_debug[i] = float(msg.data[i])

    def effort_callback(self, msg):
        count = min(len(msg.data), len(LEG_EFFORT_INDICES))
        for i in range(count):
            joint_index = LEG_EFFORT_INDICES[i]
            self.latest_effort[joint_index] = float(msg.data[i])

    def joint_callback(self, msg):
        t = self._message_time(msg)
        if self.t0 is None:
            self.t0 = t
        t = t - self.t0

        positions = [math.nan] * len(JOINT_ORDER)
        velocities = [math.nan] * len(JOINT_ORDER)

        for i, name in enumerate(msg.name):
            if name not in self.name_to_index:
                continue
            target_index = self.name_to_index[name]
            if i < len(msg.position):
                positions[target_index] = float(msg.position[i])
            if i < len(msg.velocity):
                velocities[target_index] = float(msg.velocity[i])

        self._append_plot_sample(t, positions)
        self._write_csv_sample(t, positions, velocities)

    def _append_plot_sample(self, t, positions):
        self.time_history.append(t)

        for joint_name in self.selected_joints:
            index = self.name_to_index[joint_name]
            self.actual_history[joint_name].append(positions[index])
            self.desired_history[joint_name].append(self.latest_desired[index])

        # Không xóa dữ liệu cũ nữa.
        # Như vậy đồ thị sẽ giữ gốc thời gian 0 và tiếp tục vẽ về bên phải.

    def _write_csv_sample(self, t, positions, velocities):
        if self.csv_writer is None:
            return

        row = [f"{t:.6f}"]
        for i in range(len(JOINT_ORDER)):
            desired = self.latest_desired[i]
            actual = positions[i]
            error = desired - actual
            row.extend([
                self._format_float(actual),
                self._format_float(velocities[i]),
                self._format_float(desired),
                self._format_float(error),
                self._format_float(self.latest_effort[i]),
            ])
        row.extend(self._format_float(value) for value in self.latest_debug)
        self.csv_writer.writerow(row)

    @staticmethod
    def _format_float(value):
        if math.isnan(value):
            return ""
        return f"{value:.8f}"

    def update_plot(self):
        if self.figure is None or not self.time_history:
            return

        times = list(self.time_history)
        for ax, joint_name in zip(self.axes, self.selected_joints):
            actual_line, desired_line = self.lines[joint_name]
            actual_values = list(self.actual_history[joint_name])
            desired_values = list(self.desired_history[joint_name])

            actual_line.set_data(times, actual_values)
            desired_line.set_data(times, desired_values)

            # Giữ gốc x = 0, không cho trục thời gian bị trôi.
            x_max = max(self.plot_window_sec, times[-1])
            ax.set_xlim(0.0, x_max)

            # Vẫn tự co giãn trục y theo toàn bộ dữ liệu đã lưu.
            #self._autoscale_y(ax, actual_values + desired_values)

        if self.live_plot:
            self.figure.canvas.draw_idle()
            self.figure.canvas.flush_events()

    @staticmethod
    def _autoscale_y(ax, values):
        clean = [value for value in values if not math.isnan(value)]
        if not clean:
            return

        min_value = min(clean)
        max_value = max(clean)
        if abs(max_value - min_value) < 1e-6:
            min_value -= 0.1
            max_value += 0.1
        margin = 0.15 * (max_value - min_value)
        ax.set_ylim(min_value - margin, max_value + margin)

    def close(self):
        self.update_plot()
        if self.figure is not None and self.save_plot_on_exit:
            self.figure.savefig(self.plot_path, dpi=140)
            self.get_logger().info(f"Saved plot: {self.plot_path}")

        if self.csv_file is not None:
            self.csv_file.flush()
            self.csv_file.close()
            self.csv_file = None


def main(args=None):
    rclpy.init(args=args)
    node = JointPlotter()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
