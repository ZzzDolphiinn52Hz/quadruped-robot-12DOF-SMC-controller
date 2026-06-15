import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class JointMonitor(Node):
    def __init__(self):
        super().__init__('joint_monitor')

        self.sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_callback,
            10
        )

        self.get_logger().info('Joint monitor started. Listening to /joint_states')

    def joint_callback(self, msg):
        self.get_logger().info('--- Joint States ---')

        for name, pos, vel in zip(msg.name, msg.position, msg.velocity):
            self.get_logger().info(
                f'{name:20s} position = {pos: .4f}, velocity = {vel: .4f}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = JointMonitor()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()