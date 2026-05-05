
# 🐕 12-DOF Quadruped Robot: Sliding Mode Control (SMC) with ROS2 & Webots

![Webots](https://img.shields.io/badge/Webots-R2025a-blue)
![ROS2](https://img.shields.io/badge/ROS2-Humble-brightgreen)
![MATLAB](https://img.shields.io/badge/MATLAB-R2023-orange)
![C](https://img.shields.io/badge/Language-C/Python-yellow)

A highly optimized, 12 Degrees of Freedom (DOF) quadruped robot simulation developed in Webots. This project implements a custom non-linear **Sliding Mode Controller (SMC)** based on Euler-Lagrange dynamics, a **6th-order Bézier curve** gait planner, and features seamless **ROS2 integration** via a custom UDP bridge to overcome WSL2 networking limitations.

---

## 🚀 Key Features

*   **Non-linear Dynamics & Control:** Complete derivation of Euler-Lagrange equations (Mass, Coriolis, Gravity matrices) mapped into a robust Sliding Mode Control (SMC) law with chattering reduction (`sat()` function).
*   **Hybrid Control Architecture:** Utilizes highly stiff Position Control for Yaw joints (to resist lateral friction) and flexible Torque Control (SMC) for Pitch/Knee joints.
*   **Advanced Gait Planning:** Implements a 6th-order Bézier curve trajectory generator for smooth foot placement, eliminating ground-impact spikes.
*   **Multi-Mode Execution:** Supports 8 different locomotion modes including *Stand, Squat, Belly Dance, Trot, Pace, Gallop, Roll Sway,* and *Crab Walk*.
*   **ROS2 Teleoperation Bridge:** Real-time mode switching via ROS2 `/cmd_vel` topics. Features a custom Python UDP bridge designed to bypass WSL2 multicast and loopback isolation issues.
*   **Real-time MATLAB Telemetry:** A 50Hz UDP stream from the C-Controller to MATLAB Simulink/Scripts for live tracking error and trajectory plotting.

---

## 🏗️ System Architecture

The project employs an **Edge-Computing / Hardware-in-the-Loop** architecture. To maintain the critical 1000Hz frequency required for non-linear SMC stability, the core controller is embedded entirely in C. ROS2 acts as the High-Level Navigation brain.

```text
[ ROS2 Node (Ubuntu/WSL2) ] --(Twist /cmd_vel)--> [ Python UDP Bridge ]
                                                          |
                                                    (UDP Port 5556)
                                                          |
[ MATLAB Dashboard ] <--(UDP Port 5555)-- [ Webots C-Controller (1000Hz) ]
=======
# Quadruped Robot 12-DOF: Sliding Mode Control & Telemetry

![Webots](https://img.shields.io/badge/Webots-R2023+-blue.svg)
![MATLAB](https://img.shields.io/badge/MATLAB-R2021a+-orange.svg)
![C](https://img.shields.io/badge/Language-C-lightgrey.svg)
![Control](https://img.shields.io/badge/Control-SMC-red.svg)

Dự án mô phỏng và điều khiển Robot Bốn Chân (Quadruped Robot) 12 Bậc tự do (12-DOF) trong môi trường vật lý **Webots**. Hệ thống sử dụng bộ điều khiển **Sliding Mode Control (SMC)** dựa trên momen xoắn (Torque-based), kết hợp với quy hoạch quỹ đạo bằng **Đa thức Bézier Bậc 6** và bảng điều khiển trực quan thời gian thực trên **MATLAB**.

---

## 🌟 Tính Năng Nổi Bật

- **Toán học & Động lực học chuẩn xác**: Ứng dụng phương trình Euler-Lagrange và Inverse Kinematics cho mô hình 12-DOF.
- **Quỹ đạo mượt mà**: Đa thức Bézier bậc 6 (6th-order Bezier Polynomial) giúp triệt tiêu hoàn toàn lực giật (Zero Jerk) khi chân tiếp đất.
- **Điều khiển lai (Hybrid Control)**: Kết hợp Position Control để khóa cứng khớp Yaw giúp tăng lực bám đất (Traction) khi đi thẳng, và Torque Control linh hoạt khi đi ngang.
- **8 Chế độ vận hành (Gaits)**: Stand, Squat, Trot, Pace, Gallop, Side Sway, Crab Walk, v.v.
- **Viễn trắc thời gian thực (Real-time Telemetry)**: Liên tục phát sóng tọa độ không gian 4 bàn chân qua giao thức mạng UDP ở tốc độ 50Hz.
- **Sci-Fi MATLAB Dashboard**: Giao diện hiển thị quỹ đạo chân thời gian thực siêu mượt (60fps) với phong cách Dark Mode độc đáo.

---

## 📂 Cấu Trúc Thư Mục

```text
Final Dog/
├── Documents/               # Tài liệu toán học, thuật toán và phân tích kiến trúc
├── MATLAB_Scripts/          # Các script MATLAB phân tích và vẽ đồ thị (Dashboard)
├── Webots_Simulation/       # Thư mục gốc của project Webots
│   ├── worlds/              # Môi trường và mô hình Robot (.wbt)
│   └── controllers/         # Bộ điều khiển trung tâm
│       └── SMC_12DOF/       # Mã nguồn điều khiển viết bằng C (Multi-file)
└── README.md                # Hướng dẫn sử dụng
>>>>>>> 16857cac9bf6d567fe6992ac74f0c5293dabb54e
```

---

<<<<<<< HEAD
## 📂 Project Structure

```text
📦 Final Dog
 ┣ 📂 Backup/                 # Old codebase iterations
 ┣ 📂 Documents/              # Technical reports and math derivations
 ┃ ┣ 📜 Algorithm_Math.md
 ┃ ┣ 📜 Euler_Lagrange_Derivation.md
 ┃ ┗ 📜 ROS2_Webots_Usage_Guide.md
 ┣ 📂 MATLAB_Scripts/         # Telemetry plotting scripts
 ┣ 📂 ROS2_Bridge/            # Python bridge for WSL2-Windows communication
 ┃ ┗ 📜 ros2_udp_bridge.py
 ┣ 📂 Webots_Simulation/      # The core simulation environment
 ┃ ┣ 📂 controllers/
 ┃ ┃ ┗ 📂 SMC_12DOF/          # C-Core Controller (SMC, IK, Gait Planner)
 ┃ ┃   ┣ 📜 SMC_12DOF.c
 ┃ ┃   ┗ 📜 math_utils.c / .h
 ┃ ┗ 📂 worlds/               # Webots world files
 ┗ 📜 README.md               # You are here
```

---

## ⚙️ Prerequisites

1.  **Windows Host:** Webots R2023+ installed.
2.  **WSL2 (Ubuntu 22.04+):** ROS2 Humble installed.
3.  **MATLAB (Optional):** For real-time telemetry plotting.

---

## 🎮 Quick Start Guide

### Step 1: Start the Webots Simulation (Windows)
1. Open `Webots_Simulation/worlds/quad_3dof_L1L2L3_4legs.wbt` in Webots.
2. Click the **Build (Gear icon)** to compile the `SMC_12DOF` controller.
3. Click **Play**. The robot will initialize in *Stand* mode.

### Step 2: Launch the ROS2 Bridge (WSL2 Terminal 1)
Since WSL2 blocks UDP loopback to Windows, you must run the bridge script which automatically finds the Windows vEthernet Gateway IP.

```bash
# Source ROS2
source /opt/ros/humble/setup.bash

# Fix WSL2 Multicast bug
export ROS_LOCALHOST_ONLY=1

# Run the Bridge
cd "/mnt/c/Users/ADMIN/Downloads/Final Dog/ROS2_Bridge"
python3 ros2_udp_bridge.py
```

### Step 3: Teleoperate the Robot (WSL2 Terminal 2)
Open a new WSL2 terminal to publish velocity commands:

```bash
source /opt/ros/humble/setup.bash
export ROS_LOCALHOST_ONLY=1

# 1. Trot Forward (Mode 4)
ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {x: 0.5}}"

# 2. Crab Walk / Walk Sideways (Mode 8)
ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {y: 0.5}}"

# 3. Roll Sway / Belly Dance (Mode 7)
ros2 topic pub /cmd_vel geometry_msgs/Twist "{angular: {z: 0.5}}"

# 4. Stop (Press Ctrl+C to stop publishing. The bridge will return to Stand Mode).
```

---

## 📚 Documentation
For a deep dive into the mathematics and code design, please refer to the files in the `Documents/` directory:
- [Euler-Lagrange Derivation](Documents/Euler_Lagrange_Derivation.md): Step-by-step proof of the $M, C, G$ matrices.
- [Algorithm Math](Documents/Algorithm_Math.md): Detailed explanation of the 6th-order Bézier trajectory and IK.

---
*Developed as a Robotics Control Systems Project.*
=======
## ⚙️ Yêu Cầu Hệ Thống (Prerequisites)

Để chạy được dự án này, máy tính của bạn cần cài đặt:
1. **[Webots](https://cyberbotics.com/)** (Khuyến nghị phiên bản R2023 trở lên).
2. **Trình biên dịch C/C++** (Đi kèm sẵn khi cài Webots, hoặc cài thêm GCC/MinGW/MSVC).
3. **[MATLAB](https://www.mathworks.com/)** (Khuyến nghị R2021a trở lên, cấu hình Java Sockets tích hợp sẵn).

---

## 🚀 Hướng Dẫn Sử Dụng (How to Run)

### Bước 1: Khởi động Mô phỏng (Webots)
1. Mở phần mềm **Webots**.
2. Chọn `File -> Open World...` và trỏ đến file:  
   `Webots_Simulation/worlds/quad_3dof_L1L2L3_4legs.wbt`.
3. *(Chỉ cần làm ở lần đầu)*: Trên thanh menu, chọn biểu tượng **Bánh răng (Build)** để biên dịch lại mã nguồn C trong thư mục `controllers/SMC_12DOF`. Quá trình build sẽ tự động gộp (link) các file `.c` lại với nhau dựa trên `Makefile` đã cung cấp.
4. Nhấn **Play** để mô phỏng bắt đầu chạy.

### Bước 2: Kích hoạt Bảng Điều Khiển (MATLAB)
1. Mở phần mềm **MATLAB**.
2. Đổi thư mục làm việc (Current Folder) trỏ vào thư mục `MATLAB_Scripts/`.
3. Chạy file `realtime_dashboard.m` bằng cách gõ lệnh `realtime_dashboard` vào Command Window hoặc bấm nút **Run**.
4. Giao diện **Sci-Fi Dashboard** sẽ hiện ra, vẽ trực tiếp quỹ đạo 4 bàn chân Robot theo thời gian thực (Zero-latency) nhờ đồng bộ qua mạng UDP (Port 5555).

---

## 🛠 Tùy Chỉnh Chế Độ (Change Modes)

Để thay đổi dáng đi của Robot, bạn hãy mở file điều khiển lõi `SMC_12DOF.c` và chỉnh sửa hằng số `MODE` ở dòng số 9:
```c
#define MODE 4 // Sửa số 4 thành các số từ 1 đến 8
```
Danh sách các chế độ hỗ trợ:
- `1`: Stand (Đứng yên)
- `2`: Squat (Ngồi xổm)
- `3`: Belly Dance (Nhún nhảy tại chỗ)
- `4`: Trot (Đi nước kiệu chéo chân)
- `5`: Pace (Đi kiểu lạc đà)
- `6`: Gallop (Phi nước đại)
- `7`: Side Sway (Lắc ngang 3D)
- `8`: Crab Walk (Đi ngang như cua)

Sau khi chỉnh sửa `MODE`, bạn nhớ bấm **Build** lại trong Webots rồi mới chạy nhé.

---

## 📖 Tài Liệu Tham Khảo Thêm
Mọi công thức tính toán và phân tích kiến trúc sâu hơn đều nằm trong thư mục `Documents/`. Hãy đọc hai file `Project_Analysis.md` và `Algorithm_Math.md` để hiểu cặn kẽ về toán học đằng sau dự án này.

---
*Dự án phát triển cho mục đích học thuật và nghiên cứu Robot 12-DOF.*
