# BÁO CÁO PHÂN TÍCH KIẾN TRÚC DỰ ÁN QUADRUPED ROBOT 12-DOF

Dự án này là một hệ thống mô phỏng và điều khiển toàn diện cho một Robot bốn chân (Quadruped Robot) 12 bậc tự do (12-DOF) hoạt động trong môi trường Webots. Trái tim của hệ thống là bộ điều khiển trượt (Sliding Mode Control - SMC) thuần túy dựa trên Momen xoắn (Torque-based Control) và hệ thống viễn trắc (Telemetry) thời gian thực.

---

## 1. Cấu Trúc Thư Mục Dự Án (Project Architecture)

Sau quá trình tối ưu và chuẩn hóa, dự án được chia thành 4 phân vùng chính, tuân thủ tiêu chuẩn của các dự án Robotics chuyên nghiệp:

1. **`Backup/Stable_V1_12DOF/`**: Lưu trữ các phiên bản mã nguồn đã chạy ổn định, đóng vai trò như một điểm khôi phục an toàn (Restore point).
2. **`Documents/`**: Chứa toàn bộ tài liệu lý thuyết, công thức toán học và báo cáo kiến trúc hệ thống.
3. **`MATLAB_Scripts/`**: 
   - Chứa công cụ hiển thị đồ thị Real-time (`realtime_dashboard.m`) giúp vẽ quỹ đạo di chuyển của 4 chân trực tiếp từ Webots thông qua giao thức UDP.
   - Các file script dùng để nghiên cứu và Prototype thuật toán (ví dụ: `test_done_ver2.m`).
4. **`Webots_Simulation/`**: Dự án mô phỏng Webots lõi.
   - **`worlds/`**: Môi trường vật lý và file định nghĩa Robot (`.wbt`).
   - **`controllers/SMC_12DOF/`**: Mã nguồn C điều khiển lõi (C-Core Controller).

---

## 2. Phân Tích Bộ Điều Khiển Lõi (C-Core Controller)

Bộ điều khiển được lập trình bằng ngôn ngữ C (đảm bảo tốc độ thực thi siêu cao ở chu kỳ 1ms / 1000Hz). Để tối ưu hóa việc quản lý và Fix bug, mã nguồn đã được Module hóa:

### 2.1. Module Toán học (`math_utils.c` & `math_utils.h`)
Module này hoàn toàn độc lập với API của Webots, chuyên xử lý các tác vụ tính toán nặng:
- **`get_bezier_point()`**: Sinh quỹ đạo bước đi bằng đa thức Bézier bậc 6 (6th-order polynomial) dựa trên 7 điểm kiểm soát. Đảm bảo bàn chân chạm đất và nhấc lên với vận tốc/gia tốc bằng 0, loại bỏ hoàn toàn lực giật (Jerk).
- **`phase_to_u()`**: Chuyển đổi biến chu kỳ thời gian (Phase) thành tham số biến thiên liên tục $u \in [0,1]$ cho quỹ đạo, có tích hợp hệ số `beta_t` (Hệ số nhịp bước - Duty Factor) để phân chia rõ ràng pha Đứng (Stance) và pha Đung đưa (Swing).
- **`sat()`**: Hàm bão hòa (Saturation) dùng trong SMC để loại bỏ hiện tượng Chattering (Rung dao động) tàn phá động cơ.

### 2.2. Module Điều khiển Chính (`SMC_12DOF.c`)
- **Tần số điều khiển**: Hoạt động chặt chẽ ở 1000Hz (TIME_STEP = 1ms).
- **Điều khiển lai (Hybrid Control)**:
  - Để giải quyết bài toán mất lực ma sát (Traction) ở chân do các rung động vi mô của Torque Control, hệ thống áp dụng cơ chế Hybrid:
  - Khi Robot đi tiến/lùi (Trot, Pace, Gallop): 4 khớp Yaw được khóa cứng bằng Position Control, 8 khớp Pitch/Knee hoạt động bằng Torque Control.
  - Khi Robot đi ngang (Crab Walk): Hệ thống tự động chuyển cả 12 khớp sang Torque Control để tạo lực linh hoạt.
- **UDP Telemetry Broadcast**: Tích hợp Winsock2 để liên tục "bắn" tọa độ không gian $(X, Z)$ của 4 bàn chân ra cổng UDP 5555 với tốc độ 50Hz, cho phép phần mềm bên thứ 3 (MATLAB) vẽ đồ thị realtime mà không làm chậm mô phỏng.

---

## 3. Các Chế Độ Vận Hành (Operating Modes)

Robot hỗ trợ 8 chế độ vận hành (Modes) được kích hoạt thông qua macro `MODE`:
1. **Stand**: Đứng thẳng cân bằng.
2. **Squat**: Ngồi xổm (hạ thấp trọng tâm).
3. **Belly Dance**: Lắc lư thân mình để kiểm tra Inverse Kinematics.
4. **Trot**: Đi nước kiệu (Chân chéo góc di chuyển cùng nhau - Dáng đi cân bằng và phổ biến nhất).
5. **Pace**: Đi kiểu lạc đà (Hai chân cùng một bên di chuyển cùng lúc).
6. **Gallop**: Phi nước đại.
7. **Side Sway**: Lắc lư theo trục ngang (Trục Y).
8. **Crab Walk**: Đi bộ ngang như cua.

---

## 4. Tổng Kết Ưu Điểm Hệ Thống
1. **Kiến trúc Mở**: C controller siêu nhẹ, MATLAB đóng vai trò Observer, dễ dàng mở rộng thêm Camera AI hoặc ROS2 sau này.
2. **Bám quỹ đạo xuất sắc**: Việc chuyển đổi từ hàm Sin/Cos sang Bézier Curve giúp robot không bị "cày" chân xuống sàn hoặc nhấc quá cao lãng phí năng lượng.
3. **Độ ổn định SMC cao**: Hoàn toàn không dùng PID truyền thống, SMC cho phép robot miễn nhiễm với các nhiễu động về khối lượng và ma sát mặt sàn nhờ đường trượt (Sliding Surface) mạnh mẽ.
