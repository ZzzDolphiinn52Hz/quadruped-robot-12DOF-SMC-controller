# CHỨNG MINH VÀ TÍNH TOÁN MA TRẬN ĐỘNG LỰC HỌC M, C, G

Tài liệu này giải thích cách mà các nhà nghiên cứu chế tạo Robot bốn chân (như MIT Cheetah, Unitree) tính toán ra các ma trận $M, C, G$ trong phương trình động lực học tổng quát để tìm ra Mô-men xoắn (Torque) cần thiết cho động cơ.

Phương trình động lực học tổng quát của một hệ Robot (hoặc một cái chân robot) có dạng:
$$ M(q)\ddot{q} + C(q, \dot{q})\dot{q} + G(q) = \tau $$

---

## 1. Phương pháp Euler-Lagrange
Để tìm ra các ma trận này, chúng ta không dùng các định luật Newton cơ bản (vì tính toán lực ràng buộc tại các khớp quay cực kỳ phức tạp). Thay vào đó, ta dùng **phương pháp năng lượng Euler-Lagrange**.

Hàm Lagrange $L$ của hệ thống được định nghĩa là hiệu số giữa **Động năng ($K$)** và **Thế năng ($P$)**:
$$ L = K - P $$

Sau khi có hàm $L$, ta áp dụng phương trình Euler-Lagrange cho từng góc khớp $q_i$:
$$ \frac{d}{dt} \left( \frac{\partial L}{\partial \dot{q}_i} \right) - \frac{\partial L}{\partial q_i} = \tau_i $$
*(Đạo hàm theo thời gian của vận tốc góc trừ đi đạo hàm theo góc khớp sẽ bằng đúng lực tác động / Momen xoắn)*

---

## 2. Tính toán Động năng ($K$) và Thế năng ($P$)

Xét 1 cái chân Robot 2 bậc tự do (Gồm Đùi - Link 1 và Cẳng - Link 2) di chuyển trong không gian 2D (Sagittal plane):
- $q_1$: Góc khớp hông (Hip Pitch).
- $q_2$: Góc khớp gối (Knee Pitch).

### Bước 2.1: Động năng ($K$)
Động năng của mỗi thanh giằng bằng tổng động năng tịnh tiến của khối tâm (Center of Mass - COM) và động năng quay quanh khối tâm:
$$ K = K_1 + K_2 = \left( \frac{1}{2} m_1 v_{c1}^2 + \frac{1}{2} I_1 \dot{q}_1^2 \right) + \left( \frac{1}{2} m_2 v_{c2}^2 + \frac{1}{2} I_2 (\dot{q}_1 + \dot{q}_2)^2 \right) $$

Sử dụng Động học thuận (Forward Kinematics) để tính vận tốc $v_{c1}, v_{c2}$ dựa trên $q_1, q_2$. Sau khi bình phương và rút gọn, ta sẽ thu được một biểu thức rất dài.

### Bước 2.2: Thế năng ($P$)
Thế năng do trọng lực Trái đất tác dụng lên khối tâm của hai thanh giằng:
$$ P = P_1 + P_2 = -m_1 g (r_1 \cos q_1) - m_2 g (L_1 \cos q_1 + r_2 \cos(q_1 + q_2)) $$
*(Lưu ý: Dấu trừ tùy thuộc vào hệ quy chiếu, ở đây ta giả sử gốc tọa độ là khớp Hip, chĩa thẳng xuống dưới là chiều dương của trục Z).*

---

## 3. Trích xuất các ma trận M, C, G

Sau khi lấy đạo hàm các kiểu con đà điểu từ hàm $L = K - P$ theo công thức Euler-Lagrange, ta sẽ "gom nhóm" các hệ số lại để ra được 3 ma trận $M, C, G$.

### 3.1 Ma trận Quán tính (Inertia Matrix) - $M(q)$
Nhóm tất cả các hệ số đi kèm với gia tốc góc ($\ddot{q}_1, \ddot{q}_2$). Ma trận này biểu diễn **sự kháng cự lại sự thay đổi vận tốc** của cái chân. Nó phụ thuộc vào việc cái chân đang duỗi thẳng hay gập lại (góc $q_2$).

$$ M_{11} = I_1 + I_2 + m_1 r_1^2 + m_2 (L_1^2 + r_2^2 + 2 L_1 r_2 \cos(q_2)) $$
$$ M_{12} = M_{21} = I_2 + m_2 (r_2^2 + L_1 r_2 \cos(q_2)) $$
$$ M_{22} = I_2 + m_2 r_2^2 $$
> Nhận xét: $M(q)$ là một ma trận đối xứng dương xác định. Khi $q_2 = 0$ (chân duỗi thẳng), $M_{11}$ đạt cực đại $\rightarrow$ quay chân lúc duỗi thẳng sẽ nặng (tốn nhiều Torque) hơn lúc gập chân!

### 3.2 Ma trận Coriolis & Ly tâm - $C(q, \dot{q})$
Nhóm tất cả các hệ số chứa $\dot{q}_i^2$ (Lực ly tâm) và $\dot{q}_1 \dot{q}_2$ (Lực Coriolis). Các lực này sinh ra do **cái chân đang quay với vận tốc cao**.

$$ C_1 = -m_2 L_1 r_2 \sin(q_2) \cdot \dot{q}_2 \cdot (2\dot{q}_1 + \dot{q}_2) $$
$$ C_2 = m_2 L_1 r_2 \sin(q_2) \cdot \dot{q}_1^2 $$
> Nhận xét: Nếu robot đi chậm, $\dot{q}$ gần bằng 0 thì Ma trận $C \approx 0$ (có thể bỏ qua để tối ưu tính toán). Nhưng với robot chạy nhảy (Gallop, nhảy lộn vòng), lực ly tâm $C$ này lại cực kỳ lớn, nếu không tính đến thì robot sẽ gãy chân hoặc bay màu!

### 3.3 Véc-tơ Trọng Lực (Gravity Vector) - $G(q)$
Phần còn lại thu được từ đạo hàm của Thế năng $P$. Đây là **momen xoắn tối thiểu chỉ để giữ cho cái chân không bị rớt xuống đất** trong không khí.

$$ G_1 = m_1 g r_1 \sin(q_1) + m_2 g (L_1 \sin(q_1) + r_2 \sin(q_1+q_2)) $$
$$ G_2 = m_2 g r_2 \sin(q_1+q_2) $$

---

## Tổng kết: Tại sao lại cần M, C, G để tính Torque?
Nếu bạn dùng PID: $\tau = K_p \cdot e + K_d \cdot \dot{e}$. Nó giống như mù mờ nhắm mắt đẩy xe, đẩy tới khi nào khớp tới đích thì thôi. Rất giật cục và thiếu chính xác.

Nếu bạn dùng Động lực học:
$$ \tau_{eq} = M(q)\ddot{q}_d + C(q, \dot{q})\dot{q} + G(q) $$
Bạn đang **tiên đoán trước (Feed-forward)** chính xác đến từng Newton-mét lực kéo cần thiết, dựa trên sự phân bổ khối lượng, lực ly tâm khi quay nhanh, và sức kéo của Trái đất. Momen xoắn này sẽ triệt tiêu hoàn toàn khối lượng của cái chân, khiến cái chân trở nên "không trọng lượng" trong môi trường. Sau đó SMC chỉ cần bù thêm một lượng momen xoắn rất nhỏ ($K \cdot \text{sat}$) để sửa các sai số ma sát là robot đi mượt như lụa!

---

## 4. Thực tế tính toán trong Controller Robot (SMC_12DOF)

Dựa trên mã nguồn hiện tại của hệ thống điều khiển `SMC_12DOF.c` và `math_utils.c`, các thông số lý thuyết được triển khai vào thực tế tính toán như sau:

### 4.1. Các Ma trận Động lực học $M, C, G$
Trong code điều khiển, ma trận được tính toán tương ứng với phương trình Euler-Lagrange 2 bậc tự do (Pitch và Knee) cho mỗi chân:
- **Ma trận Khối lượng/Quán tính $M(q)$**:
  - $M_{11} = I_1 + I_2 + m_1 r_1^2 + m_2 (L_1^2 + r_2^2 + 2 L_1 r_2 \cos(q_2))$
  - $M_{12} = M_{21} = I_2 + m_2 (r_2^2 + L_1 r_2 \cos(q_2))$
  - $M_{22} = I_2 + m_2 r_2^2$
- **Thành phần Ly tâm và Coriolis $C(q, \dot{q})$**:
  - $C_1 = -m_2 L_1 r_2 \sin(q_2) \cdot \dot{q}_2 \cdot (2\dot{q}_1 + \dot{q}_2)$
  - $C_2 = m_2 L_1 r_2 \sin(q_2) \cdot \dot{q}_1^2$
- **Thành phần Trọng lực $G(q)$**:
  - $G_1 = m_1 g r_1 \sin(q_1) + m_2 g (L_1 \sin(q_1) + r_2 \sin(q_1+q_2))$
  - $G_2 = m_2 g r_2 \sin(q_1+q_2)$

### 4.2. Tính toán Lực phản lực mặt đất (GRF) và Ma trận Jacobian $J^T F_{ext}$
Để bù lại lực tác động từ mặt đất lên hệ thống cơ bắp khi robot di chuyển:
- **Lực phản lực $F_y$ (Ground Reaction Force)** được phân bổ đều lên các chân đang chạm đất:
  $$ F_y = \frac{M_{BODY} \cdot g}{num\_stance} \times contact[i] $$
  Trong đó, $num\_stance$ là tổng số chân đang nằm trong pha Stance, và $contact[i]$ là trạng thái (0 hoặc 1) của chân thứ $i$.
- **Ma trận Jacobian bù Torque $J^T F_{ext}$**:
  - $J^T F_1 = F_y \cdot (L_1 \sin(q_1) + L_2 \sin(q_1+q_2))$
  - $J^T F_2 = F_y \cdot (L_2 \sin(q_1+q_2))$

### 4.3. Dáng đi (Gaits) và Chu kỳ Swing - Stance
Robot hỗ trợ đa dạng các dáng đi điều khiển qua các mode nhận từ ROS2:
- **Tư thế tĩnh**: STAND, SQUAT, BELLY DANCE.
- **Dáng di chuyển (Gaits)**: TROT (Mode 4), PACE (Mode 5), GALLOP (Mode 6), CRAB WALK (Mode 8), SIDE SWAY (Mode 7).

**Chu kỳ pha (Phase Cycle) của dáng đi TROT (Chính)**:
- Robot có **tần số bước (fp) là 1.0 Hz** $\rightarrow$ **Chu kỳ $T = 1.0 s$**.
- Dáng đi Trot có **độ trễ pha (Phase offset)** giữa các chân như sau: `FL=0.0, FR=0.5, RL=0.5, RR=0.0` (Chân chéo di chuyển cùng lúc).
- **Hệ số pha Stance (Duty Cycle)** được thiết lập là $\beta_u = 0.60$.
- Theo thuật toán nội suy `phase_to_u()`, chân sẽ nằm trong **pha chống (Stance Phase)** nếu biến nội suy $u$ nằm trong khoảng:
  $$ \frac{1 - \beta_u}{2} \leq u \leq \frac{1 + \beta_u}{2} \implies 0.2 \leq u \leq 0.8 $$
  **Kết luận**: Thời gian bàn chân tiếp đất (Stance) chiếm **60%** chu kỳ, thời gian nhấc chân lăng trên không (Swing) chiếm **40%** chu kỳ.

### 4.4. Đa thức và Điểm kiểm soát Bézier (Bézier Polynomials)
Để tạo quỹ đạo Swing mượt mà, chân robot sử dụng **Đa thức Bézier bậc 6** (6th Order Bezier Curve) định nghĩa bởi 7 điểm kiểm soát ($W_0 \dots W_6$):
- **Các hàm cơ sở (Basis Functions)** với $v = 1 - u$:
  $$ B_0 = v^6, B_1 = 6uv^5, B_2 = 15u^2v^4, B_3 = 20u^3v^3, B_4 = 15u^4v^2, B_5 = 6u^5v, B_6 = u^6 $$
- **Các điểm kiểm soát tọa độ X ($W_x$)** ($dx$ tỷ lệ thuận với chiều dài bước $step\_length$):
  $$ W_x = [0, \; 0.8dx, \; dx, \; 0, \; -dx, \; -0.8dx, \; 0] $$
- **Các điểm kiểm soát tọa độ Z ($W_z$)** ($h$ là chiều cao bước nhấc $step\_height$):
  $$ W_z = [h, \; 0.6h, \; 0.2h, \; 0, \; 0.2h, \; 0.6h, \; h] $$
Quỹ đạo cuối cùng $x_{bz}, z_{bz}$ là tổng hợp tích của các điểm kiểm soát với các hàm cơ sở tương ứng ($x_{bz} = \sum W_{xi} B_i$, $z_{bz} = \sum W_{zi} B_i$).
