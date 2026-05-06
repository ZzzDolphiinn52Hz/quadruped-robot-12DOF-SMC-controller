# HƯỚNG DẪN KHỞI CHẠY HỆ THỐNG WEBOTS + ROS2 (UBUNTU 22.04 NATIVE)

Tài liệu này tổng hợp toàn bộ quy trình từ A-Z để khởi động và điều khiển Robot chó 12-DOF bằng ROS2 trực tiếp trên môi trường **Ubuntu 22.04 LTS (Native)**. Hệ thống không còn sử dụng WSL2 và Windows, giúp việc thiết lập mạng UDP loopback và biên dịch trở nên đơn giản, ổn định hơn.

---

## BƯỚC 1: KHỞI ĐỘNG WEBOTS

1. Mở phần mềm **Webots** trên Ubuntu.
   - Nếu cài qua snap, có thể mở bằng lệnh: `webots`
2. Trong Webots, mở file World mô phỏng: 
   `Version 2 (ROS2)/Webots_Simulation/worlds/quad_3dof_L1L2L3_4legs.wbt`
3. Đảm bảo file điều khiển C `SMC_12DOF.c` đã được biên dịch thành công cho Linux. 
   - Bấm vào biểu tượng **Bánh răng - Build** trên thanh công cụ của Webots. Trình biên dịch (GCC) sẽ tạo file chạy phù hợp với môi trường POSIX.
4. Bấm nút **Play** (hoặc Run) để bắt đầu mô phỏng. 
   - *Lúc này, Robot sẽ đứng yên ở tư thế Stand (Mode 1).*
   - *Trên Console của Webots sẽ hiện dòng chữ: `--- HE THONG DIEU KHIEN SMC CHO ROBOT 12-DOF: ĐÃ KẾT NỐI UDP ROS2 ---`*

---

## BƯỚC 2: KHỞI CHẠY ROS2 BRIDGE

Mở **Terminal số 1** trên Ubuntu và thực hiện các lệnh sau:

```bash
# 1. Kích hoạt môi trường ROS2 Humble
source /opt/ros/humble/setup.bash

# 2. Di chuyển đến thư mục chứa code Bridge
# Lưu ý thay đổi đường dẫn phù hợp với máy của bạn
cd ~/Downloads/Github/Quadruped-robot-12DOF-main/"Version/Version 2 (ROS2)/ROS2_Bridge"

# 3. Chạy file Python Node
python3 ros2_udp_bridge.py
```

*Ghi chú: Khác với WSL2, Ubuntu native hỗ trợ Multicast và UDP loopback (`127.0.0.1`) hoàn hảo. Script bridge sẽ tự động nhận diện IP `127.0.0.1` và bắt đầu lắng nghe trên topic `/cmd_vel`.*

---

## BƯỚC 3: ĐIỀU KHIỂN ROBOT BẰNG ROS2

Mở **Terminal số 2** trên Ubuntu, giữ nguyên Terminal 1 đang chạy Bridge.

```bash
# 1. Kích hoạt môi trường ROS2
source /opt/ros/humble/setup.bash
```

echo "MODE:1" | nc -u 127.0.0.1 5556

echo "MODE:4" | nc -u 127.0.0.1 5556

echo "MODE:6" | nc -u 127.0.0.1 5556


**Các câu lệnh điều khiển (Copy/Paste vào Terminal 2):**

*👉 **Mode 4 (Trot - Đi nước kiệu tới trước):***
```bash
ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {x: 0.5}}"
```

*👉 **Mode 8 (Crab Walk - Đi bò ngang như cua):***
```bash
ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {y: 0.5}}"
```

*👉 **Mode 7 (Roll Sway - Lắc lư nghiêng người sang hai bên):***
```bash
ros2 topic pub /cmd_vel geometry_msgs/Twist "{angular: {z: 0.5}}"
```

*👉 **Dừng lại (Chuyển về Stand):***
Bấm `Ctrl + C` ở Terminal 2 để ngắt lệnh gửi. Hệ thống (qua Bridge) sẽ tự động bắt diện vận tốc bằng 0 và gửi UDP trả robot về tư thế đứng yên (Mode 1).

---

## SO SÁNH VỚI MÔI TRƯỜNG WSL2 CŨ

Việc chuyển sang Ubuntu Native mang lại các lợi ích mạng và hiệu năng sau:
- **Loopback ổn định:** Không cần tìm Gateway IP của Windows vEthernet nữa. `127.0.0.1` hoạt động tức thì cho UDP 5555 và 5556.
- **ROS2 Discovery:** Không còn cần biến môi trường `ROS_LOCALHOST_ONLY=1`. Tính năng DDS (Data Distribution Service) của ROS2 được hoạt động tự nhiên không bị chặn bởi tường lửa ảo của Windows.
- **Biên dịch:** Sử dụng POSIX Socket (`<sys/socket.h>`) chuẩn của Linux thay vì thư viện WinSock2 của Windows, giúp việc phát triển dễ dàng mở rộng cho các bo mạch nhúng Linux thực tế trong tương lai.
