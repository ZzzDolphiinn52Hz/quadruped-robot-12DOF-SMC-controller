#include <webots/robot.h>
#include <webots/motor.h>
#include <webots/position_sensor.h>
#include <stdio.h>
#include <math.h>
#include <winsock2.h> // Thêm thư viện mạng UDP

#define TIME_STEP 1
#define PI 3.141592653589793
#define MODE 4 // 1: Stand, 2: Squat, 3: Belly Dance, 4: Trot, 5: Pace, 6: Gallop, 7: Side Sway, 8: Crab Walk

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

const double lambda_yaw = 100.0;
const double k_gain_yaw = 20.0; // Gain cho khớp Yaw cực lớn để giữ cứng chân

/* --- HÀM BÃO HÒA SAT --- */
double sat(double sigma, double p) {
    if (sigma > p) return 1.0;
    if (sigma < -p) return -1.0;
    return sigma / p;
}

/* --- HÀM TẠO QUỸ ĐẠO BÉZIER (Từ MATLAB) --- */
double phase_to_u(double xi, double beta_t, double beta_u) {
    xi = fmod(xi, 1.0);
    if (xi < 0) xi += 1.0;
    
    double xi1 = (1.0 - beta_t) / 2.0;
    double xi2 = (1.0 + beta_t) / 2.0;
    
    if (xi < xi1) {
        return xi * (beta_u - 1.0) / (beta_t - 1.0);
    } else if (xi <= xi2) {
        return beta_u * (2.0 * xi - 1.0) / (2.0 * beta_t) + 0.5;
    } else {
        return beta_u / 2.0 - ((beta_u - 1.0) * (beta_t - 2.0 * xi + 1.0)) / (2.0 * (beta_t - 1.0)) + 0.5;
    }
}

void get_bezier_point(double u, double d, double h, double *x_out, double *z_out) {
    // 7 Control Points W0...W6
    double dx = -0.7 * d; // Đảo dấu để sửa lỗi đi lùi
    double Wx[7] = {0, dx*(4.0/5.0), dx, 0, -dx, -dx*(4.0/5.0), 0};
    double Wz[7] = {h, h*(3.0/5.0), h*(1.0/5.0), 0, h*(1.0/5.0), h*(3.0/5.0), h};
    
    // Bezier 6th order polynomials
    double u2 = u*u;
    double u3 = u2*u;
    double u4 = u3*u;
    double u5 = u4*u;
    double u6 = u5*u;
    
    double v = 1.0 - u;
    double v2 = v*v;
    double v3 = v2*v;
    double v4 = v3*v;
    double v5 = v4*v;
    double v6 = v5*v;
    
    double B0 = v6;
    double B1 = 6.0 * u * v5;
    double B2 = 15.0 * u2 * v4;
    double B3 = 20.0 * u3 * v3;
    double B4 = 15.0 * u4 * v2;
    double B5 = 6.0 * u5 * v;
    double B6 = u6;
    
    *x_out = Wx[0]*B0 + Wx[1]*B1 + Wx[2]*B2 + Wx[3]*B3 + Wx[4]*B4 + Wx[5]*B5 + Wx[6]*B6;
    *z_out = Wz[0]*B0 + Wz[1]*B1 + Wz[2]*B2 + Wz[3]*B3 + Wz[4]*B4 + Wz[5]*B5 + Wz[6]*B6;
}

int main(int argc, char **argv) {
    wb_robot_init();

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
        
        // HYBRID CONTROL: Mode 1-6 dùng Position Control cho khớp Yaw để chống trượt
        if ((MODE <= 6) && (i % 3 == 0)) {
            wb_motor_set_position(motors[i], 0.0);
        } else {
            wb_motor_set_position(motors[i], INFINITY); // Dùng Torque Control
        }
    }
    
    // Khởi tạo hệ thống phát sóng UDP (Telemetry)
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2,2), &wsaData);
    SOCKET udp_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    struct sockaddr_in dest;
    dest.sin_family = AF_INET;
    dest.sin_port = htons(5555);
    dest.sin_addr.s_addr = inet_addr("127.0.0.1");

    double q_old[12] = {0}, qd_old[12] = {0}, dqd_old[12] = {0};
    printf("--- HE THONG DIEU KHIEN SMC CHO ROBOT 12-DOF (EULER-LAGRANGE): ONLINE (MODE %d) ---\n", MODE);

    while (wb_robot_step(TIME_STEP) != -1) {
        double t = wb_robot_get_time();
        
        // --- GAIT PLANNER ---
        double z_offset = -0.22; 
        double xd[4] = {0}, zd[4] = {z_offset, z_offset, z_offset, z_offset};
        double q0d[4] = {0}; // Quỹ đạo góc cho khớp Yaw
        int contact[4] = {1, 1, 1, 1}; 
        double num_stance = 0;

        if (MODE == 1) { // STAND
            for(int i=0; i<4; i++) zd[i] = z_offset;
        } 
        else if (MODE == 2) { // SQUAT
            for(int i=0; i<4; i++) zd[i] = -0.15;
        }
        else if (MODE == 3) { // BELLY DANCE
            for(int i=0; i<4; i++) zd[i] = z_offset + 0.04 * sin(2 * PI * 0.8 * t);
        }
        else if (MODE == 4) { // WALKING (TROT GAIT) - BÉZIER TỪ MATLAB
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
        else if (MODE == 5) { // PACE GAIT
            double f = 1.0, Ax = 0.03, Az = 0.025;
            double phi_phase[4] = {0, PI, 0, PI}; 
            for (int i = 0; i < 4; i++) {
                double p = 2 * PI * f * t + phi_phase[i];
                xd[i] = -Ax * cos(p); 
                if (sin(p) > 0) { zd[i] = z_offset + Az * sin(p); contact[i] = 0; } 
                else { zd[i] = z_offset; contact[i] = 1; }
            }
        }
        else if (MODE == 6) { // GALLOP GAIT
            double f = 1.2, Ax = 0.05, Az = 0.04; 
            double phi_phase[4] = {0, 0, 3*PI/2, 3*PI/2}; 
            for (int i = 0; i < 4; i++) {
                double p = 2 * PI * f * t + phi_phase[i];
                xd[i] = -Ax * cos(p); 
                if (sin(p) > 0) { zd[i] = z_offset + Az * sin(p); contact[i] = 0; } 
                else { zd[i] = z_offset; contact[i] = 1; }
            }
        }
        else if (MODE == 7) { // SIDE SWAY (Lắc hông trái phải)
            double f = 0.8, Ayaw = 0.15; // Biên độ góc lắc
            for (int i = 0; i < 4; i++) {
                zd[i] = z_offset; // Đứng yên 4 chân
                // Tất cả các chân cùng nghiêng về 1 phía để lắc thân sang ngang
                q0d[i] = Ayaw * sin(2 * PI * f * t); 
            }
        }
        else if (MODE == 8) { // CRAB WALK (Đi bò ngang như cua)
            double f = 1.0, Ayaw = 0.1, Az = 0.03;
            double phi_phase[4] = {0, PI, PI, 0}; // Nhấc chân chéo như Trot
            for (int i = 0; i < 4; i++) {
                double p = 2 * PI * f * t + phi_phase[i];
                // Swing sang phải, đạp sang trái (hoặc ngược lại) đồng bộ cho 4 chân
                q0d[i] = -Ayaw * cos(p); 
                if (sin(p) > 0) { 
                    zd[i] = z_offset + Az * sin(p); contact[i] = 0; 
                } else {
                    zd[i] = z_offset; contact[i] = 1; 
                }
            }
        }

        for(int i=0; i<4; i++) num_stance += contact[i];
        if (num_stance == 0) num_stance = 4.0; 

        // Bắn UDP Telemetry cho 4 chân về MATLAB
        static double last_log_time = 0;
        if (t - last_log_time >= 0.02) { // 50Hz là đủ siêu mượt cho đồ thị
            char buffer[256];
            // Format: t, x0, z0, x1, z1, x2, z2, x3, z3
            sprintf(buffer, "%f,%f,%f,%f,%f,%f,%f,%f,%f", 
                    t, xd[0], zd[0], xd[1], zd[1], xd[2], zd[2], xd[3], zd[3]);
            sendto(udp_sock, buffer, strlen(buffer), 0, (struct sockaddr *)&dest, sizeof(dest));
            last_log_time = t;
        }

        // --- ĐIỀU KHIỂN ĐỘNG LỰC HỌC CHO 4 CHÂN ---
        for (int i = 0; i < 4; i++) {
            int idx_yaw = i * 3;
            int idx_pitch = i * 3 + 1;
            int idx_knee = i * 3 + 2;

            double q0 = wb_position_sensor_get_value(sensors[idx_yaw]);
            double q1 = wb_position_sensor_get_value(sensors[idx_pitch]);
            double q2 = wb_position_sensor_get_value(sensors[idx_knee]);
            if (isnan(q0) || isnan(q1) || isnan(q2)) continue;
            
            double dq0 = (q0 - q_old[idx_yaw]) / (TIME_STEP / 1000.0);
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
            double dq0d = (q0d[i] - qd_old[idx_yaw]) / (TIME_STEP / 1000.0);
            double dq1d = (q1d - qd_old[idx_pitch]) / (TIME_STEP / 1000.0);
            double dq2d = (q2d - qd_old[idx_knee]) / (TIME_STEP / 1000.0);
            qd_old[idx_yaw] = q0d[i];
            qd_old[idx_pitch] = q1d; 
            qd_old[idx_knee] = q2d;

            // Gia tốc IK
            double ddq0d = (dq0d - dqd_old[idx_yaw]) / (TIME_STEP / 1000.0);
            double ddq1d = (dq1d - dqd_old[idx_pitch]) / (TIME_STEP / 1000.0);
            double ddq2d = (dq2d - dqd_old[idx_knee]) / (TIME_STEP / 1000.0);
            dqd_old[idx_yaw] = dq0d;
            dqd_old[idx_pitch] = dq1d;
            dqd_old[idx_knee] = dq2d;

            // ----------------------------------------------------
            // SMC CHO KHỚP YAW (Chỉ chạy Torque Control khi MODE >= 7)
            // ----------------------------------------------------
            double tau0 = 0;
            double F_y = (M_BODY * g / num_stance) * contact[i];

            if (MODE >= 7) {
                double s0 = (dq0d - dq0) + lambda_yaw * (q0d[i] - q0);
                double s_dot_ref0 = ddq0d + lambda_yaw * (dq0d - dq0);
                
                double L_eff = L1*cos(q1) + L2*cos(q1+q2); 
                double G0 = F_y * L_eff * sin(q0); 
                double M00 = 0.05; 

                tau0 = M00 * s_dot_ref0 + G0 + k_gain_yaw * sat(s0, 0.1); 
                tau0 = fmax(fmin(tau0, 20.0), -20.0);
                wb_motor_set_torque(motors[idx_yaw], tau0);
            }

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
        }
    }
    closesocket(udp_sock);
    WSACleanup();
    wb_robot_cleanup();
    return 0;
}
