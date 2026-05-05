# TÍNH TOÁN LÝ THUYẾT VÀ THUẬT TOÁN ĐIỀU KHIỂN

Tài liệu này trình bày toàn bộ các cơ sở toán học, từ khâu sinh quỹ đạo (Trajectory Generation), động học nghịch (Inverse Kinematics) cho đến động lực học và luật điều khiển trượt (Sliding Mode Control) được áp dụng trong dự án Quadruped 12-DOF.

---

## 1. Hệ Tham Số Vật Lý Hệ Thống

Robot được mô hình hóa với các thông số vật lý cốt lõi sau:
- **Khối lượng thân máy (Body):** $M_{body} = 1.0 \text{ kg}$
- **Gia tốc trọng trường:** $g = 9.81 \text{ m/s}^2$
- **Khối lượng đùi (Link 1):** $m_1 = 0.12 \text{ kg}$
- **Khối lượng cẳng (Link 2):** $m_2 = 0.08 \text{ kg}$
- **Chiều dài đùi & cẳng:** $L_1 = L_2 = 0.16 \text{ m}$

Mô-men quán tính quanh trọng tâm (COM) của mỗi thanh giằng:
- $I_1 = \frac{1}{12} m_1 L_1^2 \approx 0.000256 \text{ kg}\cdot\text{m}^2$
- $I_2 = \frac{1}{12} m_2 L_2^2 \approx 0.00017067 \text{ kg}\cdot\text{m}^2$

---

## 2. Quy Hoạch Quỹ Đạo Bézier (Trajectory Generation)

Để tạo ra dáng đi tự nhiên, thay vì sử dụng các hàm Sin/Cos đơn giản, hệ thống sử dụng **Đa thức Bézier Bậc 6 (6th-order Bezier Polynomial)**. 

Phương trình tham số của đường cong Bézier bậc $n$ là:
$$ B(u) = \sum_{i=0}^{n} C_n^i (1-u)^{n-i} u^i W_i \quad \text{với } u \in [0,1] $$

Áp dụng cho $n=6$, ta có 7 Điểm kiểm soát (Control Points) $W_0, \dots, W_6$. Để chân vươn tới sải bước $d$ và nhấc cao $h$, các điểm này được ánh xạ:
- $W_x = [0, \quad 0.8 dx, \quad dx, \quad 0, \quad -dx, \quad -0.8 dx, \quad 0]$
- $W_z = [h, \quad 0.6 h, \quad 0.2 h, \quad 0, \quad 0.2 h, \quad 0.6 h, \quad h]$

> **Lợi ích:** Quỹ đạo này đảm bảo vận tốc và gia tốc ở điểm chạm đất ($u=0$ và $u=1$) đều tiến về 0, giúp chân tiếp đất "êm ái" mà không gây ra lực giật cục (Jerk).

---

## 3. Động Học Nghịch (Inverse Kinematics)

Nhiệm vụ của Động học nghịch là tìm ra các góc khớp $\theta_d$ (Hip Pitch) và $\phi_d$ (Knee Pitch) để bàn chân đạt được tọa độ không gian $(X_d, Z_d)$ do bộ tạo quỹ đạo cung cấp.

Áp dụng Định lý Cosin trong tam giác tạo bởi đùi và cẳng:
$$ D = \frac{X_d^2 + Z_d^2 - L_1^2 - L_2^2}{2 L_1 L_2} $$

Góc khớp Gối (Knee Pitch):
$$ q_{2d} = -\arccos(D) $$
*(Lưu ý: Luôn chọn nghiệm âm để khớp gối bẻ gập về phía sau - Backward Knee).*

Góc khớp Đùi (Hip Pitch):
$$ q_{1d} = \text{atan2}(X_d, -Z_d) - \text{atan2}(L_2 \sin(q_{2d}), L_1 + L_2 \cos(q_{2d})) $$

---

## 4. Mô Hình Động Lực Học (Dynamics Modeling)

Phương trình Động lực học Euler-Lagrange mô tả lực tương tác của 1 chân:
$$ M(q)\ddot{q} + C(q, \dot{q})\dot{q} + G(q) = \tau + J^T F_{ext} $$

Trong đó:
- **Ma trận Khối lượng/Quán tính $M(q)$**: Phụ thuộc vào vị trí của khớp gối.
  - $M_{11} = I_1 + I_2 + m_1 r_1^2 + m_2 (L_1^2 + r_2^2 + 2 L_1 r_2 \cos(q_2))$
  - $M_{22} = I_2 + m_2 r_2^2$
- **Ma trận Coriolis & Ly tâm $C(q, \dot{q})$**: Lực sinh ra do vận tốc quay của khớp.
- **Véc-tơ Trọng lực $G(q)$**: Lực kéo xuống của Trái đất.
- **Ngoại lực mặt đất $J^T F_{ext}$**: Phản lực khi bàn chân chạm đất, được chia đều cho số chân đang đứng.
  - $F_y = \frac{M_{body} \cdot g}{\text{Số chân chạm đất}}$

---

## 5. Luật Điều Khiển Trượt (Sliding Mode Control - SMC)

Sliding Mode Control (SMC) là phương pháp điều khiển phi tuyến siêu bền vững. Thay vì điều khiển trực tiếp, SMC "ép" hệ thống trượt dọc theo một mặt phẳng toán học được định nghĩa trước.

### 5.1 Định Nghĩa Mặt Trượt (Sliding Surface)
Định nghĩa sai số bám: $e = q_d - q$
Mặt trượt được định nghĩa:
$$ s = \dot{e} + \lambda e $$
Đạo hàm mặt trượt:
$$ \dot{s} = \ddot{q}_d - \ddot{q} + \lambda (\dot{q}_d - \dot{q}) $$

### 5.2 Áp dụng Luật Điều Khiển
Thế phương trình hệ thống vào $\dot{s}$ và ép buộc hệ thống bám theo luật hàm số mũ $\dot{s} = -K \cdot \text{sat}(s, \Phi)$, ta tính được Momen xoắn $\tau$ cần cung cấp cho động cơ:

$$ \tau_{eq} = M(q) \left[ \ddot{q}_d + \lambda (\dot{q}_d - \dot{q}) \right] + C(q, \dot{q}) + G(q) + J^T F_{ext} $$
$$ \tau_{SMC} = \tau_{eq} + K \cdot \text{sat}(s, \Phi) $$

- **$\tau_{eq}$ (Thành phần bù tương đương)**: Sử dụng các phương trình vật lý (M, C, G) để "triệt tiêu" hoàn toàn trọng lượng và lực quán tính của cái chân.
- **$K \cdot \text{sat}(s, \Phi)$ (Thành phần sửa sai)**: Sửa chữa những sai số do nhiễu môi trường, ma sát mòn, hoặc sai lệch đo đạc. Việc dùng hàm bão hòa `sat()` thay cho hàm dấu `sign()` giúp xóa bỏ triệt để hiện tượng gầm rú/rung giật (Chattering) ở động cơ.

### 5.3 Các Gain (Hệ số điều khiển) Tối Ưu
Quá trình Tuning trên Webots đã rút ra bộ tham số "vàng" sau:
- **$\lambda = 50.0$**: Tốc độ hội tụ cực nhanh.
- **$K = 2.0$**: Khả năng chống nhiễu vừa đủ (do chân khá nhẹ).
- **$\Phi = 1.0$**: Lớp biên bão hòa dày, giúp robot tiếp đất siêu êm ái mà không bị trượt trên sàn cứng.
