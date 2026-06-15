#ifndef MATH_UTILS_H
#define MATH_UTILS_H

#include <math.h>

double sat(double sigma, double p);
double phase_to_u(double xi, double beta_t, double beta_u);
void get_bezier_point(double u, double d, double h, double *x_out, double *z_out);

#endif
