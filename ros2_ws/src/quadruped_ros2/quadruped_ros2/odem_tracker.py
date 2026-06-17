import math

import rclpy
from geometry_msgs.msg import PointStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix


class OdemTracker(Node):
    """Publish planar odometry from the Webots world-position GPS.

    Webots world is configured as NUE in this project:
      Webots X = north/forward-world axis
      Webots Y = up
      Webots Z = east/side-world axis

    ROS odom published here uses:
      odom.x = Webots X - initial X
      odom.y = Webots Z - initial Z
      odom.z = Webots Y - initial Y
    """

    def __init__(self):
        super().__init__("odem_tracker")

        self.declare_parameter("gps_point_topic", "/quad_3dof_L123/base_gps")
        self.declare_parameter("gps_fix_topic", "/quad_3dof_L123/base_gps/fix")
        self.declare_parameter("odem_topic", "/odem")
        self.declare_parameter("odom_alias_topic", "/odom")
        self.declare_parameter("frame_id", "odom")
        self.declare_parameter("child_frame_id", "base_link")
        self.declare_parameter("reset_origin", True)
        self.declare_parameter("direction_log_period", 1.0)

        self.frame_id = self.get_parameter("frame_id").value
        self.child_frame_id = self.get_parameter("child_frame_id").value
        self.reset_origin = bool(self.get_parameter("reset_origin").value)
        self.direction_log_period = float(
            self.get_parameter("direction_log_period").value
        )

        odem_topic = self.get_parameter("odem_topic").value
        odom_alias_topic = self.get_parameter("odom_alias_topic").value
        gps_point_topic = self.get_parameter("gps_point_topic").value
        gps_fix_topic = self.get_parameter("gps_fix_topic").value

        self.odem_pub = self.create_publisher(Odometry, odem_topic, 10)
        self.odom_alias_pub = None
        if odom_alias_topic and odom_alias_topic != odem_topic:
            self.odom_alias_pub = self.create_publisher(Odometry, odom_alias_topic, 10)

        self.point_sub = self.create_subscription(
            PointStamped,
            gps_point_topic,
            self.point_callback,
            10,
        )
        self.fix_sub = self.create_subscription(
            NavSatFix,
            gps_fix_topic,
            self.fix_callback,
            10,
        )

        self.origin = None
        self.last_position = None
        self.last_time = None
        self.last_log_time = self.get_clock().now()
        self.received_sample = False

        self.create_timer(2.0, self.watchdog)

        self.get_logger().info(
            f"Odem tracker started. Listening GPS PointStamped on {gps_point_topic}, "
            f"publishing {odem_topic}"
        )
        if self.odom_alias_pub is not None:
            self.get_logger().info(f"Also publishing alias {odom_alias_topic}")

    def point_callback(self, msg):
        # Webots GPS local coordinates are x, y(up), z.
        self.handle_webots_position(
            webots_x=float(msg.point.x),
            webots_y=float(msg.point.y),
            webots_z=float(msg.point.z),
            stamp=msg.header.stamp,
        )

    def fix_callback(self, msg):
        # Fallback if the Webots GPS is configured as WGS84. This is less useful
        # for the current local Webots world, but keeps the node alive if the
        # driver publishes NavSatFix instead of PointStamped.
        if math.isnan(msg.latitude) or math.isnan(msg.longitude):
            return

        earth_radius_m = 6378137.0
        lat = math.radians(float(msg.latitude))
        lon = math.radians(float(msg.longitude))
        altitude = float(msg.altitude) if not math.isnan(msg.altitude) else 0.0

        if self.origin is None:
            self._wgs84_origin = (lat, lon, altitude)
            self.origin = (0.0, 0.0, 0.0)

        lat0, lon0, alt0 = getattr(self, "_wgs84_origin", (lat, lon, altitude))
        east = (lon - lon0) * earth_radius_m * math.cos(lat0)
        north = (lat - lat0) * earth_radius_m
        up = altitude - alt0

        self.publish_odom(north, east, up, msg.header.stamp)

    def handle_webots_position(self, webots_x, webots_y, webots_z, stamp):
        if self.origin is None:
            self.origin = (
                webots_x if self.reset_origin else 0.0,
                webots_y if self.reset_origin else 0.0,
                webots_z if self.reset_origin else 0.0,
            )
            self.get_logger().info(
                "Captured odem origin: "
                f"webots_x={webots_x:.4f}, webots_y={webots_y:.4f}, "
                f"webots_z={webots_z:.4f}"
            )

        origin_x, origin_y, origin_z = self.origin

        odom_x = webots_x - origin_x
        odom_y = webots_z - origin_z
        odom_z = webots_y - origin_y

        self.publish_odom(odom_x, odom_y, odom_z, stamp)

    def publish_odom(self, odom_x, odom_y, odom_z, stamp):
        self.received_sample = True
        now = self.get_clock().now()
        if stamp.sec == 0 and stamp.nanosec == 0:
            stamp = now.to_msg()

        vx = 0.0
        vy = 0.0
        vz = 0.0
        if self.last_position is not None and self.last_time is not None:
            dt = (now - self.last_time).nanoseconds * 1e-9
            if dt > 0.0:
                last_x, last_y, last_z = self.last_position
                vx = (odom_x - last_x) / dt
                vy = (odom_y - last_y) / dt
                vz = (odom_z - last_z) / dt

        self.last_position = (odom_x, odom_y, odom_z)
        self.last_time = now

        msg = Odometry()
        msg.header.stamp = stamp
        msg.header.frame_id = self.frame_id
        msg.child_frame_id = self.child_frame_id

        msg.pose.pose.position.x = odom_x
        msg.pose.pose.position.y = odom_y
        msg.pose.pose.position.z = odom_z
        msg.pose.pose.orientation.w = 1.0

        msg.twist.twist.linear.x = vx
        msg.twist.twist.linear.y = vy
        msg.twist.twist.linear.z = vz

        # Mark orientation covariance unknown/high because GPS alone does not
        # measure robot yaw.
        msg.pose.covariance[0] = 0.0001
        msg.pose.covariance[7] = 0.0001
        msg.pose.covariance[14] = 0.0001
        msg.pose.covariance[21] = 999.0
        msg.pose.covariance[28] = 999.0
        msg.pose.covariance[35] = 999.0

        self.odem_pub.publish(msg)
        if self.odom_alias_pub is not None:
            self.odom_alias_pub.publish(msg)

        elapsed = (now - self.last_log_time).nanoseconds * 1e-9
        if elapsed >= self.direction_log_period:
            self.last_log_time = now
            direction = "forward/+world_x" if vx > 0.001 else "reverse/-world_x" if vx < -0.001 else "near_zero"
            self.get_logger().info(
                f"odem x={odom_x:.4f}, y={odom_y:.4f}, vx={vx:.4f} m/s, "
                f"direction={direction}"
            )

    def watchdog(self):
        if self.received_sample:
            return
        self.get_logger().warn(
            "No GPS samples yet. Check `ros2 topic list | grep base_gps`. "
            "If /base_gps is missing, Webots did not expose the GPS device."
        )


def main(args=None):
    rclpy.init(args=args)
    node = OdemTracker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == "__main__":
    main()
