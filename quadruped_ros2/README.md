# 🐕 12-DOF Quadruped Robot: Sliding Mode Control (SMC) with ROS2 & Webots

![Webots](https://img.shields.io/badge/Webots-R2023+-blue.svg)
![ROS2](https://img.shields.io/badge/ROS2-Humble-brightgreen)
![MATLAB](https://img.shields.io/badge/MATLAB-R2023-orange)
![C](https://img.shields.io/badge/Language-C/Python-yellow)
![Control](https://img.shields.io/badge/Control-SMC-red.svg)

Dự án mô phỏng và điều khiển Robot Bốn Chân (Quadruped Robot) 12 Bậc tự do (12-DOF) trong môi trường vật lý **Webots**. Hệ thống sử dụng bộ điều khiển **Sliding Mode Control (SMC)** dựa trên momen xoắn (Torque-based), kết hợp với quy hoạch quỹ đạo bằng **Đa thức Bézier Bậc 6** và hỗ trợ điều khiển qua **ROS2 trên Ubuntu 22.04 LTS native**.

A highly optimized, 12 Degrees of Freedom (DOF) quadruped robot simulation developed in Webots. This project implements a custom non-linear **Sliding Mode Controller (SMC)** based on Euler-Lagrange dynamics, a **6th-order Bézier curve** gait planner, and features seamless **ROS2 integration** via a custom UDP bridge natively on Ubuntu 22.04.

---

## 🌟 Tính Năng Nổi Bật / Key Features

- **Toán học & Động lực học chuẩn xác (Non-linear Dynamics)**: Ứng dụng phương trình Euler-Lagrange và Inverse Kinematics cho mô hình 12-DOF.
- **Quỹ đạo mượt mà (Advanced Gait Planning)**: Đa thức Bézier bậc 6 giúp triệt tiêu hoàn toàn lực giật (Zero Jerk) khi chân tiếp đất.
- **Điều khiển lai (Hybrid Control Architecture)**: Kết hợp Position Control để khóa cứng khớp Yaw giúp tăng lực bám đất (Traction), và Torque Control (SMC) linh hoạt cho các khớp Pitch/Knee.
- **8 Chế độ vận hành (Multi-Mode Execution)**: Stand, Squat, Belly Dance, Trot, Pace, Gallop, Roll Sway, Crab Walk.
- **Tích hợp ROS2 Native (ROS2 Teleoperation)**: Điều khiển thời gian thực qua topic `/cmd_vel` trên Ubuntu 22.04 LTS (không còn phụ thuộc WSL2).
- **Viễn trắc thời gian thực (Real-time Telemetry)**: Liên tục phát sóng tọa độ không gian 4 bàn chân qua UDP ở tốc độ 50Hz cho MATLAB Dashboard.

---

## 🏗️ System Architecture

The project employs an **Edge-Computing / Hardware-in-the-Loop** architecture. To maintain the critical 1000Hz frequency required for non-linear SMC stability, the core controller is embedded entirely in C. ROS2 acts as the High-Level Navigation brain.

```text
[ ROS2 Node (Ubuntu 22.04) ] --(Twist /cmd_vel)--> [ Python UDP Bridge ]
                                                          |
                                                    (UDP Port 5556)
                                                          |
[ MATLAB Dashboard ] <--(UDP Port 5555)-- [ Webots C-Controller (1000Hz) ]
```

---

## 📂 Project Structure / Cấu Trúc Thư Mục

```text
📦 Version 2 (ROS2)
 ┣ 📂 Backup/                 # Old codebase iterations
 ┣ 📂 Documents/              # Tài liệu toán học, thuật toán và phân tích kiến trúc
 ┃ ┣ 📜 Algorithm_Math.md
 ┃ ┣ 📜 Euler_Lagrange_Derivation.md
 ┃ ┣ 📜 Project_Analysis.md
 ┃ ┗ 📜 ROS2_Webots_Usage_Guide.md # Hướng dẫn chạy Webots + ROS2
 ┣ 📂 MATLAB_Scripts/         # Telemetry plotting scripts (Dashboard)
 ┣ 📂 ROS2_Bridge/            # Python bridge for ROS2-Webots communication
 ┃ ┗ 📜 ros2_udp_bridge.py
 ┗ 📂 Webots_Simulation/      # Môi trường Webots
   ┣ 📂 controllers/
   ┃ ┗ 📂 SMC_12DOF/          # C-Core Controller (POSIX Sockets)
   ┃   ┣ 📜 SMC_12DOF.c
   ┃   ┣ 📜 math_utils.c / .h
   ┃   ┗ 📜 Makefile
   ┗ 📂 worlds/               # Webots world files
```

---

## ⚙️ Yêu Cầu Hệ Thống / Prerequisites

1. **OS:** Ubuntu 22.04 LTS (Native)
2. **Webots:** Phiên bản R2023 trở lên (`sudo snap install webots`)
3. **ROS2:** Bản phát hành Humble (`ros-humble-desktop`)
4. **MATLAB (Optional):** Khuyến nghị R2021a trở lên cho Real-time Dashboard.

---

## 🎮 Hướng Dẫn Khởi Chạy Nhanh / Quick Start Guide

### Bước 1: Khởi động Webots (Terminal 1)
1. Mở Webots và load file world:
   `Webots_Simulation/worlds/quad_3dof_L1L2L3_4legs.wbt`
2. Bấm vào biểu tượng **Bánh răng (Build)** để Webots biên dịch mã nguồn C (`SMC_12DOF.c` dùng POSIX Sockets).
3. Bấm **Play** để mô phỏng bắt đầu (Robot đứng ở Stand mode).

### Bước 2: Chạy ROS2 UDP Bridge (Terminal 2)
Mở terminal Ubuntu mới và chạy Bridge để nhận lệnh từ ROS2 chuyển qua Webots:

```bash
source /opt/ros/humble/setup.bash
cd ~/Downloads/Github/Quadruped-robot-12DOF-main/"Version/Version 2 (ROS2)/ROS2_Bridge"
python3 ros2_udp_bridge.py
```

### Bước 3: Điều Khiển Bằng ROS2 (Terminal 3)
Mở terminal Ubuntu mới và gửi lệnh:

```bash
source /opt/ros/humble/setup.bash

# 1. Trot Forward (Mode 4)
ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {x: 0.5}}"

# 2. Crab Walk / Walk Sideways (Mode 8)
ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {y: 0.5}}"

# 3. Roll Sway / Belly Dance (Mode 7)
ros2 topic pub /cmd_vel geometry_msgs/Twist "{angular: {z: 0.5}}"

# 4. Stop
# Bấm Ctrl+C, Bridge sẽ tự chuyển Webots về Mode 1 (Stand).
```

---

## 📚 Tài Liệu Tham Khảo Thêm / Documentation
Mọi công thức tính toán và phân tích kiến trúc sâu hơn đều nằm trong thư mục `Documents/`:
- [Euler-Lagrange Derivation](Documents/Euler_Lagrange_Derivation.md): Step-by-step proof of the $M, C, G$ matrices.
- [Algorithm Math](Documents/Algorithm_Math.md): Detailed explanation of the 6th-order Bézier trajectory and IK.
- [Usage Guide](Documents/ROS2_Webots_Usage_Guide.md): Hướng dẫn chi tiết chạy ROS2.

---
*Dự án phát triển cho mục đích học thuật và nghiên cứu Robot 12-DOF.*
