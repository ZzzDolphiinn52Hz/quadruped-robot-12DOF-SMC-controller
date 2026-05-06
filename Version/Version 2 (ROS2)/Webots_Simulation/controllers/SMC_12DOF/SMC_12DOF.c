#include <webots/robot.h>
#include <webots/motor.h>
#include <webots/position_sensor.h>
#include <stdio.h>
#include <math.h>
#include <sys/socket.h>  // POSIX sockets
#include <arpa/inet.h>   // inet_addr
#include <unistd.h>      // close()
#include <fcntl.h>       // fcntl() cho non-blocking
#include <string.h>      // strlen, strncmp
#include <stdlib.h>      // atoi
#include "math_utils.h"

#define TIME_STEP 1
#define PI 3.141592653589793
/* --- THÔNG SỐ CƠ HỌC CHO 12-DOF (Chuẩn Euler-Lagrange) --- */
const double L1 = 0.16, L2 = 0.16; 
const double M_BODY = 1.0;         

// Thông số động lực học chân (Dynamics parameters)
const double m1 = 0.12;   // Khối lượng đùi (kg)
const double m2 = 0.08;   // Khối lượng cẳng chân (kg)
const double r1 = 0.08;   // Khoảng cách từ khớp đến trọng tâm đùi (L1/2)
const double r2 = 0.08;   // Khoảng cách từ khớp đến trọng tâm cẳng chân (L2/2)
const double I1 = 0.000256; // Quán tính đùi (1/12 * m1 * L1^2)
const double I2 = 0.00017067; // Quán tính cẳng (1/12 * m2 * L2^2)
const double g = 9.81;

/* --- SMC GAINS --- */
const double lambda = 50.0;     
const double k_gain = 2.0;    
const double phi_smc = 1.0;

int main(int argc, char **argv) {
    wb_robot_init();
    int current_mode = 4; // Mode mặc định
    int last_mode = -1;

    WbDeviceTag motors[12], sensors[12];
    char *motor_names[12] = {
        "FL_hip_yaw", "FL_hip_pitch", "FL_knee_pitch",
        "FR_hip_yaw", "FR_hip_pitch", "FR_knee_pitch",
        "RL_hip_yaw", "RL_hip_pitch", "RL_knee_pitch",
        "RR_hip_yaw", "RR_hip_pitch", "RR_knee_pitch"
    };
    
    for (int i = 0; i < 12; i++) {
        motors[i] = wb_robot_get_device(motor_names[i]);
        char s_name[50]; sprintf(s_name, "%s_sensor", motor_names[i]);
        sensors[i] = wb_robot_get_device(s_name);
        wb_position_sensor_enable(sensors[i], TIME_STEP);
        
        // YAW KHỚP LUÔN LUÔN DÙNG POSITION CONTROL (Khóa cứng để chống xoắn chân)
        // PITCH VÀ KNEE DÙNG TORQUE CONTROL (SMC)
        if (i % 3 == 0) {
            wb_motor_set_position(motors[i], 0.0);
        } else {
            wb_motor_set_position(motors[i], INFINITY); 
        }
    }
    
    // Khởi tạo hệ thống phát sóng UDP (Telemetry)
    int udp_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    struct sockaddr_in dest;
    dest.sin_family = AF_INET;
    dest.sin_port = htons(5555);       // SMC Dashboard (smc_dashboard.m)
    dest.sin_addr.s_addr = inet_addr("127.0.0.1");

    // Socket thứ 2 cho Kinematic Dashboard (realtime_dashboard.m)
    int udp_sock2 = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    struct sockaddr_in dest2;
    dest2.sin_family = AF_INET;
    dest2.sin_port = htons(5557);      // Kinematic Dashboard
    dest2.sin_addr.s_addr = inet_addr("127.0.0.1");

    // Khởi tạo hệ thống nhận UDP (Nhận lệnh từ ROS2)
    int udp_recv_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    struct sockaddr_in recv_addr;
    memset(&recv_addr, 0, sizeof(recv_addr));
    recv_addr.sin_family = AF_INET;
    recv_addr.sin_port = htons(5556);
    recv_addr.sin_addr.s_addr = INADDR_ANY;
    if (bind(udp_recv_sock, (struct sockaddr *)&recv_addr, sizeof(recv_addr)) < 0) {
        perror("LỖI: BIND PORT 5556 THẤT BẠI");
    }

    // Cài đặt Non-blocking socket để không làm dừng vòng lặp Webots
    int flags = fcntl(udp_recv_sock, F_GETFL, 0);
    fcntl(udp_recv_sock, F_SETFL, flags | O_NONBLOCK);

    double q_old[12] = {0}, qd_old[12] = {0}, dqd_old[12] = {0};
    printf("--- HE THONG DIEU KHIEN SMC CHO ROBOT 12-DOF: ĐÃ KẾT NỐI UDP ROS2 ---\n");

    while (wb_robot_step(TIME_STEP) != -1) {
        double t = wb_robot_get_time();
        
        // --- NHẬN LỆNH ĐIỀU KHIỂN TỪ ROS2 QUA UDP ---
        char recv_buf[256];
        int bytes_read = recv(udp_recv_sock, recv_buf, sizeof(recv_buf)-1, 0);
        if (bytes_read > 0) {
            recv_buf[bytes_read] = '\0';
            // ROS2 gửi lệnh dạng: "MODE:4"
            if (strncmp(recv_buf, "MODE:", 5) == 0) {
                int new_mode = atoi(&recv_buf[5]);
                if (new_mode >= 1 && new_mode <= 10) {
                    current_mode = new_mode;
                }
            }
        }

        // Cập nhật Mode (Không cần update Hybrid Control nữa vì Yaw luôn là Position Control)
        if (current_mode != last_mode) {
            printf("[ROS2 UDP] Chuyen mode -> %d\n", current_mode);
            last_mode = current_mode;
        }
        
        // --- GAIT PLANNER ---
        double z_offset = -0.22; 
        double xd[4] = {0}, zd[4] = {z_offset, z_offset, z_offset, z_offset};
        double q0d[4] = {0}; // Quỹ đạo góc cho khớp Yaw
        int contact[4] = {1, 1, 1, 1}; 
        double num_stance = 0;

        if (current_mode == 1) { // STAND
            for(int i=0; i<4; i++) zd[i] = z_offset;
        } 
        else if (current_mode == 2) { // SQUAT
            for(int i=0; i<4; i++) zd[i] = -0.15;
        }
        else if (current_mode == 3) { // BELLY DANCE
            for(int i=0; i<4; i++) zd[i] = z_offset + 0.04 * sin(2 * PI * 0.8 * t);
        }
        else if (current_mode == 4) { // WALKING (TROT GAIT) - BÉZIER TỪ MATLAB
            double fp = 1.0; // Tần số bước (Hz)
            double T = 1.0 / fp; // Chu kỳ
            double beta_t = 0.60;
            double beta_u = 0.60;
            double step_d = 0.04; // Chiều dài bước (Thu nhỏ lại để dáng đi đẹp hơn)
            double step_h = 0.025; // Chiều cao bước
            
            // Pha bù (Phase offset) giống trong MATLAB: FL=0, FR=0.5, RL=0.5, RR=0
            double phase_offset[4] = {0.0, 0.5, 0.5, 0.0}; 
            
            for (int i = 0; i < 4; i++) {
                double xi = fmod(t / T + phase_offset[i], 1.0);
                double u = phase_to_u(xi, beta_t, beta_u);
                
                double x_bz, z_bz;
                get_bezier_point(u, step_d, step_h, &x_bz, &z_bz);
                
                xd[i] = x_bz;
                zd[i] = z_offset + z_bz;
                
                // Cờ contact: Nếu u nằm trong đoạn (1-beta_u)/2 đến (1+beta_u)/2 thì là stance
                double u_stance_start = (1.0 - beta_u) / 2.0; // 0.2
                double u_stance_end = (1.0 + beta_u) / 2.0;   // 0.8
                
                if (u >= u_stance_start && u <= u_stance_end) {
                    contact[i] = 1; // Chạm đất
                } else {
                    contact[i] = 0; // Đang nhấc chân
                }
            }
        }
        else if (current_mode == 5) { // PACE GAIT
            double f = 1.0, Ax = 0.03, Az = 0.025;
            double phi_phase[4] = {0, PI, 0, PI}; 
            for (int i = 0; i < 4; i++) {
                double p = 2 * PI * f * t + phi_phase[i];
                xd[i] = -Ax * cos(p); 
                if (sin(p) > 0) { zd[i] = z_offset + Az * sin(p); contact[i] = 0; } 
                else { zd[i] = z_offset; contact[i] = 1; }
            }
        }
        else if (current_mode == 6) { // GALLOP GAIT
            double f = 1.2, Ax = 0.05, Az = 0.04; 
            double phi_phase[4] = {0, 0, 3*PI/2, 3*PI/2}; 
            for (int i = 0; i < 4; i++) {
                double p = 2 * PI * f * t + phi_phase[i];
                xd[i] = -Ax * cos(p); 
                if (sin(p) > 0) { zd[i] = z_offset + Az * sin(p); contact[i] = 0; } 
                else { zd[i] = z_offset; contact[i] = 1; }
            }
        }
        else if (current_mode == 7) { // BODY ROLL SWAY (Lắc thân - Yaw + Z phối hợp)
            double f = 0.8, Az = 0.03, Ayaw = 0.15;
            double phase = sin(2 * PI * f * t);
            for (int i = 0; i < 4; i++) {
                xd[i] = 0;
                if (i == 0 || i == 2) { // FL, RL (chân trái)
                    zd[i] = z_offset + Az * phase;
                    q0d[i] = Ayaw * phase;   // Yaw ra ngoài khi nhún lên
                } else {                      // FR, RR (chân phải)
                    zd[i] = z_offset - Az * phase;
                    q0d[i] = -Ayaw * phase;  // Yaw ra ngoài khi nhún lên
                }
                contact[i] = 1; // 4 chân luôn chạm đất
            }
        }
        else if (current_mode == 8) { // LATERAL TROT (Đi ngang kiểu Trot - Crab Walk V2)
            double f = 0.8, Ayaw = 0.18, Az = 0.03;
            double phi_phase[4] = {0, PI, PI, 0}; // Trot pattern (chéo nhau)
            for (int i = 0; i < 4; i++) {
                double p = 2 * PI * f * t + phi_phase[i];
                // Chân trái đẩy ngược chân phải (đối xứng gương)
                double yaw_sign = (i == 0 || i == 2) ? 1.0 : -1.0;
                q0d[i] = yaw_sign * Ayaw * cos(p);
                if (sin(p) > 0) { // Swing phase
                    zd[i] = z_offset + Az * sin(p);
                    contact[i] = 0;
                } else { // Stance phase
                    zd[i] = z_offset;
                    contact[i] = 1;
                }
            }
        }
        else if (current_mode == 9) { // SPIN IN PLACE (Differential Stepping - Tank Drive)
            double fp = 0.8;
            double T = 1.0 / fp;
            double beta_t = 0.60;
            double beta_u = 0.60;
            double step_d = 0.04;    // Chiều dài bước tiến/lùi
            double step_h = 0.025;   // Chiều cao nhấc chân
            double Ayaw = 0.12;     // Yaw bổ trợ
            
            // Trot pattern: FL+RR đồng pha, FR+RL đồng pha
            double phase_offset[4] = {0.0, 0.5, 0.5, 0.0};
            
            for (int i = 0; i < 4; i++) {
                double xi = fmod(t / T + phase_offset[i], 1.0);
                double u = phase_to_u(xi, beta_t, beta_u);
                
                double x_bz, z_bz;
                get_bezier_point(u, step_d, step_h, &x_bz, &z_bz);
                
                // TANK DRIVE: Chân trái (FL=0, RL=2) bước tới
                //             Chân phải (FR=1, RR=3) bước lùi
                // → Giống bánh xích tank: trái tiến + phải lùi = xoay tại chỗ
                double x_sign = (i == 0 || i == 2) ? 1.0 : -1.0;
                xd[i] = x_sign * x_bz;
                zd[i] = z_offset + z_bz;
                
                // Yaw bổ trợ: tăng cường moment xoay
                q0d[i] = Ayaw * cos(PI * u);
                
                // Contact detection
                double u_stance_start = (1.0 - beta_u) / 2.0;
                double u_stance_end = (1.0 + beta_u) / 2.0;
                if (u >= u_stance_start && u <= u_stance_end) {
                    contact[i] = 1;
                } else {
                    contact[i] = 0;
                }
            }
        }
        else if (current_mode == 10) { // GREETING (Chó ngồi chào - Showcase 12-DOF)
            double wave_f = 1.5; // Tần số vẫy (Hz)
            double wave_t = 2 * PI * wave_f * t;
            
            for (int i = 0; i < 4; i++) {
                if (i == 0 || i == 1) { 
                    // ── FL, FR: NGỒI XUỐNG (phần mông) ──
                    xd[i] = 0.06;
                    zd[i] = -0.12;     // Co chân → hạ mông
                    q0d[i] = 0.0;
                    contact[i] = 1;
                }
                else if (i == 3) { 
                    // ── RR: CHÂN CHỐNG ĐỠ ──
                    xd[i] = 0.0;
                    zd[i] = z_offset;  // -0.22 (đứng chuẩn)
                    q0d[i] = 0.0;
                    contact[i] = 1;
                }
                else { 
                    // ── RL (i==2): VẪY TAY CHÀO ──
                    // Dơ chân THẲNG + CAO hết cỡ
                    
                    // DOF 1 - YAW: Vẫy trái/phải
                    q0d[i] = 0.35 * sin(wave_t);
                    
                    // DOF 2 - PITCH: Dướn ra trước (gần ngang = dơ cao nhất trong giới hạn khớp)
                    // xd âm = hướng trước robot, pitch ≈ -1.37 rad (giới hạn ±1.57)
                    xd[i] = -0.25 - 0.02 * sin(wave_t);
                    
                    // DOF 3 - KNEE: Gần ngang hip (zd≈-0.05 = gần ngang, chân gần thẳng)
                    // Reach ≈ 0.255m / 0.32m → khá thẳng, vẫy bàn chân tần số x2
                    zd[i] = -0.05 + 0.03 * sin(2.0 * wave_t);
                    
                    contact[i] = 0;
                }
            }
        }

        for(int i=0; i<4; i++) num_stance += contact[i];
        if (num_stance == 0) num_stance = 4.0; 

        // --- Mảng lưu trữ dữ liệu SMC cho telemetry (4 chân × 12 giá trị) ---
        double tele_q0d[4]={0}, tele_q0[4]={0};   // Yaw: desired, actual
        double tele_q1d[4]={0}, tele_q1[4]={0};   // Pitch: desired, actual
        double tele_q2d[4]={0}, tele_q2[4]={0};   // Knee: desired, actual
        double tele_s0[4]={0}, tele_s1[4]={0}, tele_s2[4]={0};  // Sliding surface
        double tele_tau1[4]={0}, tele_tau2[4]={0}; // Torque (yaw = position ctrl → không có)

        // --- ĐIỀU KHIỂN ĐỘNG LỰC HỌC CHO 4 CHÂN ---
        for (int i = 0; i < 4; i++) {
            int idx_yaw = i * 3;
            int idx_pitch = i * 3 + 1;
            int idx_knee = i * 3 + 2;

            double q0 = wb_position_sensor_get_value(sensors[idx_yaw]);
            double q1 = wb_position_sensor_get_value(sensors[idx_pitch]);
            double q2 = wb_position_sensor_get_value(sensors[idx_knee]);
            if (isnan(q0) || isnan(q1) || isnan(q2)) continue;
            
            double dq1 = (q1 - q_old[idx_pitch]) / (TIME_STEP / 1000.0);
            double dq2 = (q2 - q_old[idx_knee]) / (TIME_STEP / 1000.0);
            q_old[idx_yaw] = q0;
            q_old[idx_pitch] = q1; 
            q_old[idx_knee] = q2;

            // INVERSE KINEMATICS (IK) CHO PITCH/KNEE
            double D = (xd[i]*xd[i] + zd[i]*zd[i] - L1*L1 - L2*L2) / (2.0*L1*L2);
            D = (D > 0.99) ? 0.99 : ((D < -0.99) ? -0.99 : D);
            
            double q2d = -acos(D); 
            double q1d = atan2(xd[i], -zd[i]) - atan2(L2*sin(q2d), L1 + L2*cos(q2d));

            // Vận tốc IK
            double dq1d = (q1d - qd_old[idx_pitch]) / (TIME_STEP / 1000.0);
            double dq2d = (q2d - qd_old[idx_knee]) / (TIME_STEP / 1000.0);
            qd_old[idx_yaw] = q0d[i];
            qd_old[idx_pitch] = q1d; 
            qd_old[idx_knee] = q2d;

            // Gia tốc IK
            double ddq1d = (dq1d - dqd_old[idx_pitch]) / (TIME_STEP / 1000.0);
            double ddq2d = (dq2d - dqd_old[idx_knee]) / (TIME_STEP / 1000.0);
            dqd_old[idx_yaw] = (q0d[i] - qd_old[idx_yaw]) / (TIME_STEP / 1000.0);
            dqd_old[idx_pitch] = dq1d;
            dqd_old[idx_knee] = dq2d;

            // ----------------------------------------------------
            // ĐIỀU KHIỂN KHỚP YAW (Luôn dùng Position Control để chống vặn xoắn)
            // ----------------------------------------------------
            wb_motor_set_position(motors[idx_yaw], q0d[i]);

            double F_y = (M_BODY * g / num_stance) * contact[i];

            // ----------------------------------------------------
            // SMC CHO KHỚP PITCH VÀ KNEE (EULER-LAGRANGE)
            // ----------------------------------------------------
            double M11 = I1 + I2 + m1*r1*r1 + m2*(L1*L1 + r2*r2 + 2*L1*r2*cos(q2));
            double M12 = I2 + m2*(r2*r2 + L1*r2*cos(q2));
            double M21 = M12;
            double M22 = I2 + m2*r2*r2;

            double C1 = -m2 * L1 * r2 * sin(q2) * dq2 * (2*dq1 + dq2);
            double C2 = m2 * L1 * r2 * sin(q2) * dq1 * dq1;

            double G1 = m1*g*r1*sin(q1) + m2*g*(L1*sin(q1) + r2*sin(q1+q2));
            double G2 = m2*g*r2*sin(q1+q2);

            double J_T_F1 = F_y * (L1 * sin(q1) + L2 * sin(q1+q2));
            double J_T_F2 = F_y * (L2 * sin(q1+q2));

            double s1 = (dq1d - dq1) + lambda * (q1d - q1);
            double s2 = (dq2d - dq2) + lambda * (q2d - q2);

            double s_dot_ref1 = ddq1d + lambda * (dq1d - dq1);
            double s_dot_ref2 = ddq2d + lambda * (dq2d - dq2);

            double tau_eq1 = M11 * s_dot_ref1 + M12 * s_dot_ref2 + C1 + G1 + J_T_F1;
            double tau_eq2 = M21 * s_dot_ref1 + M22 * s_dot_ref2 + C2 + G2 + J_T_F2;

            double tau1 = tau_eq1 + k_gain * sat(s1, phi_smc);
            double tau2 = tau_eq2 + k_gain * sat(s2, phi_smc);

            // Giới hạn max torque
            tau1 = fmax(fmin(tau1, 5.0), -5.0);
            tau2 = fmax(fmin(tau2, 5.0), -5.0);

            wb_motor_set_torque(motors[idx_pitch], tau1);
            wb_motor_set_torque(motors[idx_knee], tau2);

            // --- LƯU DỮ LIỆU TELEMETRY CHO CHÂN i ---
            tele_q0d[i] = q0d[i];  tele_q0[i] = q0;
            tele_q1d[i] = q1d;     tele_q1[i] = q1;
            tele_q2d[i] = q2d;     tele_q2[i] = q2;
            tele_s0[i] = q0d[i] - q0;  // Yaw: sai số vị trí (Position Control)
            tele_s1[i] = s1;            // Pitch: sliding surface
            tele_s2[i] = s2;            // Knee: sliding surface
            tele_tau1[i] = tau1;
            tele_tau2[i] = tau2;
        }

        // --- BẮN UDP TELEMETRY ĐẦY ĐỦ CHO MATLAB (50Hz) ---
        // Format: t, [chân0: q0d,q0,q1d,q1,q2d,q2,s0,s1,s2,tau0,tau1,tau2], [chân1: ...], ...
        // = 1 + 4×12 = 49 giá trị
        static double last_log_time = 0;
        if (t - last_log_time >= 0.02) {
            char buffer[2048];
            int offset = sprintf(buffer, "%.4f", t);
            for (int i = 0; i < 4; i++) {
                offset += sprintf(buffer + offset, ",%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f",
                    tele_q0d[i], tele_q0[i],
                    tele_q1d[i], tele_q1[i],
                    tele_q2d[i], tele_q2[i],
                    tele_s0[i], tele_s1[i], tele_s2[i],
                    0.0,         tele_tau1[i], tele_tau2[i]);
            }
            sendto(udp_sock, buffer, strlen(buffer), 0, (struct sockaddr *)&dest, sizeof(dest));

            // Gửi dữ liệu XZ quỹ đạo chân cho Kinematic Dashboard (port 5557)
            char buf2[256];
            sprintf(buf2, "%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f",
                    t, xd[0], zd[0], xd[1], zd[1], xd[2], zd[2], xd[3], zd[3]);
            sendto(udp_sock2, buf2, strlen(buf2), 0, (struct sockaddr *)&dest2, sizeof(dest2));

            last_log_time = t;
        }
    }
    close(udp_recv_sock);
    close(udp_sock);
    close(udp_sock2);
    wb_robot_cleanup();
    return 0;
}
