import os

from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.webots_controller import WebotsController


def generate_launch_description():
    package_dir = get_package_share_directory('quadruped_ros2')

    world_path = os.path.join(
        package_dir,
        'worlds',
        'quad_3dof_L1L2L3_4legs.wbt'
    )

    urdf_path = os.path.join(
        package_dir,
        'urdf',
        'quadruped_webots.urdf'
    )

    controller_config = os.path.join(
        package_dir,
        'config',
        'ros2_controllers.yaml'
    )

    with open(urdf_path, 'r') as f:
        robot_description = f.read()

    robot_description = robot_description.replace(
        'CONTROLLER_CONFIG_PATH',
        controller_config
    )

    webots = WebotsLauncher(
        world=world_path
    )

    webots_controller = WebotsController(
        robot_name='quad_3dof_L123',
        parameters=[
            {'robot_description': robot_description},
            controller_config
        ]
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'joint_state_broadcaster',
            '--controller-manager',
            '/controller_manager'
        ],
        output='screen'
    )

    position_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'position_controller',
            '--controller-manager',
            '/controller_manager'
        ],
        output='screen'
    )
    main_controller_node = Node(
        package='quadruped_ros2',
        executable='quadruped_main',
        name='quadruped_main_controller',
        output='screen'
    )

    return LaunchDescription([
        webots,
        webots_controller,
        joint_state_broadcaster_spawner,
        position_controller_spawner,
        #main_controller_node
    ])