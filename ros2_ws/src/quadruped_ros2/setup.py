from setuptools import setup
import os
from glob import glob

package_name = 'quadruped_ros2'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name]
        ),
        (
            'share/' + package_name,
            ['package.xml']
        ),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')
        ),
        (
            os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')
        ),
        (
            os.path.join('share', package_name, 'worlds'),
            glob('worlds/*.wbt')
        ),
        (
            os.path.join('share', package_name, 'urdf'),
            glob('urdf/*.urdf')
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='your_name',
    maintainer_email='your_email@example.com',
    description='ROS2 Webots interface for 12-DOF quadruped robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'joint_monitor = quadruped_ros2.joint_monitor:main',
            'pose_commander = quadruped_ros2.pose_commander:main',
            'gait_controller = quadruped_ros2.gait_controller:main',
        ],
    },
)