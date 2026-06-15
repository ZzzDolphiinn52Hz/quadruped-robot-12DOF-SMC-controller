import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray


class PoseCommander(Node):
    def __init__(self):
        super().__init__('pose_commander')

        self.pub = self.create_publisher(
            Float64MultiArray,
            '/position_controller/commands',
            10
        )

        self.timer = self.create_timer(2.0, self.send_pose)
        self.toggle = False

        self.get_logger().info('Pose commander started. Publishing to /position_controller/commands')

    def send_pose(self):
        msg = Float64MultiArray()

        if self.toggle:
            # Pose 1
            msg.data = [
                0.0, 0.7, -1.4,
                0.0, 0.7, -1.4,
                0.0, 0.7, -1.4,
                0.0, 0.7, -1.4,
            ]
        else:
            # Pose 2
            msg.data = [
                0.0, 0.4, -1.0,
                0.0, 0.4, -1.0,
                0.0, 0.4, -1.0,
                0.0, 0.4, -1.0,
            ]

        self.pub.publish(msg)
        self.get_logger().info(f'Published pose: {msg.data}')

        self.toggle = not self.toggle


def main(args=None):
    rclpy.init(args=args)
    node = PoseCommander()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()