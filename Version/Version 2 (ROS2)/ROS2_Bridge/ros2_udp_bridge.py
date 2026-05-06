#!/usr/bin/env python3
# ros2_udp_bridge.py
# Nút ROS2 trung gian để giao tiếp với Webots C Controller qua UDP

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import socket

class QuadrupedUDPBridge(Node):
    def __init__(self):
        super().__init__('quadruped_udp_bridge')
        
        # Khởi tạo UDP Socket (Lấy IP của Windows Host thay vì 127.0.0.1 do lỗi mạng WSL2 UDP)
        import subprocess
        try:
            res = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True)
            self.webots_ip = res.stdout.split()[2]
        except:
            self.webots_ip = '127.0.0.1'
            
        print(f"--- ĐÃ TÌM THẤY IP WINDOWS HOST LÀ: {self.webots_ip} ---")
            
        self.cmd_port = 5556  # Cổng nhận lệnh của Webots
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Đăng ký nhận bản tin /cmd_vel (ví dụ: từ teleop_twist_keyboard)
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )
        
        self.current_mode = 1 # Mặc định là Stand
        
        self.get_logger().info('--- QUADRUPED ROS2-UDP BRIDGE STARTED ---')
        self.get_logger().info('Đang lắng nghe topic /cmd_vel...')

    def cmd_vel_callback(self, msg):
        new_mode = 1 # Chế độ đứng yên (Stand) mặc định

        # === BẢNG MODE ===
        # 1: Stand  |  2: Squat     |  3: Belly Dance  |  4: Trot Walk
        # 5: Pace   |  6: Gallop    |  7: Body Roll     |  8: Lateral Trot
        # 9: Spin   | 10: Wave Dance
        
        # Phân tích lệnh di chuyển từ ROS2
        if abs(msg.linear.x) > 0.05:
            new_mode = 4  # Trot (Đi thẳng)
        elif abs(msg.linear.y) > 0.05:
            new_mode = 8  # Lateral Trot (Đi ngang)
        elif abs(msg.angular.z) > 0.05:
            new_mode = 9  # Spin in Place (Quay tại chỗ)
            
        # Luôn gửi UDP để đảm bảo Webots nhận được lệnh ngay cả khi Webots vừa khởi động lại
        cmd_str = f"MODE:{new_mode}"
        self.sock.sendto(cmd_str.encode('utf-8'), (self.webots_ip, self.cmd_port))
        
        # Chỉ in log khi chuyển mode để đỡ rác màn hình
        if new_mode != self.current_mode:
            self.get_logger().info(f'[UDP SEND] Chuyển Webots sang -> {cmd_str}')
            self.current_mode = new_mode

def main(args=None):
    rclpy.init(args=args)
    bridge_node = QuadrupedUDPBridge()
    try:
        rclpy.spin(bridge_node)
    except KeyboardInterrupt:
        pass
    finally:
        bridge_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
