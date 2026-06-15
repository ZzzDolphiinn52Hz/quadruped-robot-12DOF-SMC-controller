import math

from quadruped_ros2.robot_config import (
    MODE_STAND,
    MODE_TROT,
    MODE_LATERAL,
    MODE_SPIN,
)
from quadruped_ros2.bezier_utils import clamp, foot_bezier_trajectory


class GaitPlanner:
    def __init__(self, config):
        self.config = config
        self.phase = 0.0
        self.current_mode = MODE_STAND

    def mode_from_cmd_vel(self, vx, vy, wz):
        if abs(wz) > 0.05:
            return MODE_SPIN

        if abs(vy) > 0.03:
            return MODE_LATERAL

        if abs(vx) > 0.005:
            return MODE_TROT

        return MODE_STAND

    def update(self, dt, vx, vy, wz):
        self.current_mode = self.mode_from_cmd_vel(vx, vy, wz)

        if self.current_mode == MODE_STAND:
            return self.stand()

        self.phase += dt / self.config.gait_period
        self.phase = self.phase % 1.0

        if self.current_mode == MODE_TROT:
            return self.trot(vx)

        if self.current_mode == MODE_LATERAL:
            return self.lateral(vy)

        if self.current_mode == MODE_SPIN:
            return self.spin(wz)

        return self.stand()

    def stand(self):
        return {
            "FL": {"yaw": 0.0, "x": 0.0, "z": self.config.z_home, "contact": True},
            "FR": {"yaw": 0.0, "x": 0.0, "z": self.config.z_home, "contact": True},
            "RL": {"yaw": 0.0, "x": 0.0, "z": self.config.z_home, "contact": True},
            "RR": {"yaw": 0.0, "x": 0.0, "z": self.config.z_home, "contact": True},
        }

    def trot(self, vx):
        speed = abs(vx)
        direction = self.config.forward_sign * (1.0 if vx >= 0.0 else -1.0)

        step_length = clamp(
            speed * 0.35,
            self.config.min_step_length,
            self.config.max_step_length
        )

        phases = {
            "FL": self.phase,
            "RR": self.phase,
            "FR": self.phase + 0.5,
            "RL": self.phase + 0.5,
        }

        leg_commands = {}

        for leg, leg_phase in phases.items():
            x, z, contact = foot_bezier_trajectory(
                phase=leg_phase,
                step_length=step_length,
                step_height=self.config.step_height,
                z_home=self.config.z_home,
                direction=direction,
                duty_factor=self.config.duty_factor,
            )

            leg_commands[leg] = {
                "yaw": 0.0,
                "x": x,
                "z": z,
                "contact": contact,
            }

        return leg_commands

    def lateral(self, vy):
        """
        Phiên bản đơn giản:
        - chưa làm IK 3D cho đi ngang thật
        - dùng hip_yaw dao động nhẹ để test crab-like motion
        """
        direction = 1.0 if vy >= 0.0 else -1.0
        yaw_amp = 0.25 * direction

        phases = {
            "FL": self.phase,
            "RR": self.phase,
            "FR": self.phase + 0.5,
            "RL": self.phase + 0.5,
        }

        leg_commands = self.stand()

        for leg, leg_phase in phases.items():
            yaw = yaw_amp * math.sin(2.0 * math.pi * leg_phase)
            leg_commands[leg]["yaw"] = yaw

        return leg_commands

    def spin(self, wz):
        """
        Phiên bản đơn giản:
        - yaw trái/phải ngược chiều nhau
        - chân vẫn giữ z_home
        """
        direction = 1.0 if wz >= 0.0 else -1.0
        yaw_amp = 0.30 * direction

        yaw_value = yaw_amp * math.sin(2.0 * math.pi * self.phase)

        return {
            "FL": {"yaw": yaw_value, "x": 0.0, "z": self.config.z_home, "contact": True},
            "FR": {"yaw": -yaw_value, "x": 0.0, "z": self.config.z_home, "contact": True},
            "RL": {"yaw": -yaw_value, "x": 0.0, "z": self.config.z_home, "contact": True},
            "RR": {"yaw": yaw_value, "x": 0.0, "z": self.config.z_home, "contact": True},
        }