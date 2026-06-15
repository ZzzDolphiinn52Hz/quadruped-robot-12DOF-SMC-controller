Sửa bước 3 — Build lại package

Tắt launch đang chạy bằng:

Ctrl + C

Sau đó chạy:

cd ~/Documents/quadruped-robot/quadruped-robot-12DOF-SMC-controller/ros2_ws

rm -rf build/quadruped_ros2 install/quadruped_ros2

colcon build --symlink-install --packages-select quadruped_ros2

source install/setup.bash
Sửa bước 4 — Dọn Webots cũ rồi chạy lại
pkill -f webots
pkill -f webots-controller
rm -rf /tmp/webots/$USER

Chạy lại:

ros2 launch quadruped_ros2 quadruped_webots.launch.py