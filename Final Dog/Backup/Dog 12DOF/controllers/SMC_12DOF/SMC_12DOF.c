#include <webots/robot.h>
#include <webots/motor.h>
#include <webots/position_sensor.h>
#include <stdio.h>
#include <math.h>

#define TIME_STEP 1
#define PI 3.141592653589793
#define MODE 6 // 1: Stand, 2: Squat, 3: Dance, 4: Trot, 5: Pace, 6: Bound

/* --- THÔNG SỐ CƠ HỌC CHO 12-DOF --- */
const double L1 = 0.16, L2 = 0.16; // Đùi và cẳng chân
const double M_BODY = 1.0;         // Khối lượng thân robot
const double g = 9.81;

/* --- SMC GAINS --- */
const double lambda = 50.0;     
const double k_gain = 2.0;    
const double phi_smc = 1.0;   // Dải bão hòa đã nới rộng để dập tắt dao động

/* --- HÀM BÃO HÒA SAT --- */
double sat(double sigma, double p) {
    if (sigma > p) return 1.0;
    if (sigma < -p) return -1.0;
    return sigma / p;
}

int main(int argc, char **argv) {
    wb_robot_init();

    /* --- KHỞI TẠO THIẾT BỊ 12 DOF --- */
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
        
        // Khóa khớp Yaw (biến robot thành 8 bậc tự do phẳng)
        if (i % 3 == 0) {
            wb_motor_set_position(motors[i], 0.0);
        } else {
            // Torque Mode cho Pitch và Knee
            wb_motor_set_position(motors[i], INFINITY); 
        }
    }

    double q_old[12] = {0}, qd_old[12] = {0};
    printf("--- HE THONG DIEU KHIEN SMC CHO ROBOT 12-DOF: ONLINE (MODE %d) ---\n", MODE);

    while (wb_robot_step(TIME_STEP) != -1) {
        double t = wb_robot_get_time();
        
        // --- GAIT PLANNER ---
        double z_offset = -0.22; 
        double xd[4] = {0}, zd[4] = {z_offset, z_offset, z_offset, z_offset};
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
        else if (MODE == 4) { // WALKING (TROT GAIT)
            double f = 1.0, Ax = 0.03, Az = 0.025;
            double phi_phase[4] = {0, PI, PI, 0}; 
            for (int i = 0; i < 4; i++) {
                double p = 2 * PI * f * t + phi_phase[i];
                // Đổi lại thành Ax * cos(p) theo phản hồi để robot đi tới trong Mode 4
                xd[i] = Ax * cos(p); 
                if (sin(p) > 0) { 
                    zd[i] = z_offset + Az * sin(p); contact[i] = 0; 
                } else {
                    zd[i] = z_offset; contact[i] = 1; 
                }
            }
        }
        else if (MODE == 5) { // PACE GAIT (Lạc đà)
            double f = 1.0, Ax = 0.03, Az = 0.025;
            double phi_phase[4] = {0, PI, 0, PI}; 
            for (int i = 0; i < 4; i++) {
                double p = 2 * PI * f * t + phi_phase[i];
                xd[i] = -Ax * cos(p); 
                if (sin(p) > 0) { zd[i] = z_offset + Az * sin(p); contact[i] = 0; } 
                else { zd[i] = z_offset; contact[i] = 1; }
            }
        }
        else if (MODE == 6) { // GALLOP GAIT (Nhảy chồm tới trước)
            double f = 1.2, Ax = 0.05, Az = 0.04; 
            // Hai chân trước nhấc, sau đó 1/4 chu kỳ hai chân sau nhấc để tạo đà phóng tới
            double phi_phase[4] = {0, 0, 3*PI/2, 3*PI/2}; 
            for (int i = 0; i < 4; i++) {
                double p = 2 * PI * f * t + phi_phase[i];
                xd[i] = -Ax * cos(p); 
                if (sin(p) > 0) { zd[i] = z_offset + Az * sin(p); contact[i] = 0; } 
                else { zd[i] = z_offset; contact[i] = 1; }
            }
        }

        // Đếm số chân đang trụ
        for(int i=0; i<4; i++) num_stance += contact[i];
        if (num_stance == 0) num_stance = 4.0; 

        // --- ĐIỀU KHIỂN CHO 4 CHÂN ---
        for (int i = 0; i < 4; i++) {
            int idx_pitch = i * 3 + 1;
            int idx_knee = i * 3 + 2;

            double q1 = wb_position_sensor_get_value(sensors[idx_pitch]);
            double q2 = wb_position_sensor_get_value(sensors[idx_knee]);
            if (isnan(q1) || isnan(q2)) continue;
            
            double dq1 = (q1 - q_old[idx_pitch]) / (TIME_STEP / 1000.0);
            double dq2 = (q2 - q_old[idx_knee]) / (TIME_STEP / 1000.0);
            q_old[idx_pitch] = q1; 
            q_old[idx_knee] = q2;

            // INVERSE KINEMATICS
            double D = (xd[i]*xd[i] + zd[i]*zd[i] - L1*L1 - L2*L2) / (2.0*L1*L2);
            D = (D > 0.99) ? 0.99 : ((D < -0.99) ? -0.99 : D);
            
            double q2d = -acos(D); 
            double q1d = atan2(xd[i], -zd[i]) - atan2(L2*sin(q2d), L1 + L2*cos(q2d));

            double dq1d = (q1d - qd_old[idx_pitch]) / (TIME_STEP / 1000.0);
            double dq2d = (q2d - qd_old[idx_knee]) / (TIME_STEP / 1000.0);
            qd_old[idx_pitch] = q1d; 
            qd_old[idx_knee] = q2d;

            // SLIDING MODE CONTROL (SMC)
            double s1 = (dq1d - dq1) + lambda * (q1d - q1);
            double s2 = (dq2d - dq2) + lambda * (q2d - q2);

            double m_load = (M_BODY / num_stance) * contact[i]; 
            double tau1 = m_load * g * (L1 * sin(q1) + L2 * sin(q1+q2))+ k_gain * sat(s1, phi_smc);
            double tau2 = m_load * g * L1 * sin(q1) + k_gain * sat(s2, phi_smc);

            tau1 = fmax(fmin(tau1, 5.0), -5.0);
            tau2 = fmax(fmin(tau2, 5.0), -5.0);

            wb_motor_set_torque(motors[idx_pitch], tau1);
            wb_motor_set_torque(motors[idx_knee], tau2);
        }
    }
    wb_robot_cleanup();
    return 0;
}
