#include "math_utils.h"

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
