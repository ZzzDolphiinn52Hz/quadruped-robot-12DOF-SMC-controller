import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/dolphiinn/Documents/quadruped-robot/quadruped-robot-12DOF-SMC-controller/ros2_ws/install/quadruped_ros2'
