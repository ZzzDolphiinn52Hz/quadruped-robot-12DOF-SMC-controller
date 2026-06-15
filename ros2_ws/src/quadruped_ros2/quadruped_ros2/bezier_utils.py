import math


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def phase_to_u(phase, duty_factor=0.5):
    """
    Đổi phase 0..1 sang tham số u.
    phase < duty_factor  : stance
    phase >= duty_factor : swing
    """
    phase = phase % 1.0

    if phase < duty_factor:
        return phase / duty_factor, True

    return (phase - duty_factor) / (1.0 - duty_factor), False


def bezier_6(points, u):
    """
    Bezier bậc 6.
    points có 7 phần tử.
    """
    if len(points) != 7:
        raise ValueError("Bezier degree 6 needs exactly 7 control points")

    u = clamp(u, 0.0, 1.0)
    one_minus_u = 1.0 - u

    value = 0.0

    for i in range(7):
        coefficient = math.comb(6, i)
        value += coefficient * ((one_minus_u) ** (6 - i)) * (u ** i) * points[i]

    return value


def foot_bezier_trajectory(phase, step_length, step_height, z_home, direction, duty_factor):
    """
    Tạo quỹ đạo bàn chân:
    - stance: bàn chân quét từ trước về sau
    - swing : bàn chân nhấc lên, đưa từ sau ra trước
    """
    u, is_stance = phase_to_u(phase, duty_factor)

    half_step = step_length / 2.0

    if is_stance:
        wx = [
            half_step,
            half_step * 0.60,
            half_step * 0.25,
            0.0,
            -half_step * 0.25,
            -half_step * 0.60,
            -half_step,
        ]

        wz = [
            z_home,
            z_home,
            z_home,
            z_home,
            z_home,
            z_home,
            z_home,
        ]

        contact = True

    else:
        wx = [
            -half_step,
            -half_step * 0.80,
            -half_step * 0.30,
            0.0,
            half_step * 0.30,
            half_step * 0.80,
            half_step,
        ]

        wz = [
            z_home,
            z_home + step_height * 0.20,
            z_home + step_height * 0.80,
            z_home + step_height,
            z_home + step_height * 0.80,
            z_home + step_height * 0.20,
            z_home,
        ]

        contact = False

    x = direction * bezier_6(wx, u)
    z = bezier_6(wz, u)

    return x, z, contact