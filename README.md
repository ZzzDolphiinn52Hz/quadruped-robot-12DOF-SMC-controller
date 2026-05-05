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
```

---

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
