import argparse
import csv
import math

from quadruped_ros2.robot_config import (
    HIP_PITCH_INDICES,
    JOINT_ORDER,
    KNEE_PITCH_INDICES,
)


def parse_float(row, key):
    value = row.get(key, "")
    if value == "":
        return math.nan
    return float(value)


def summarize_joint(rows, joint_name, joint_index):
    positions = []
    desired = []
    errors = []
    velocities = []
    efforts = []
    limit_hits = 0

    for row in rows:
        position = parse_float(row, f"{joint_name}_pos")
        target = parse_float(row, f"{joint_name}_desired")
        velocity = parse_float(row, f"{joint_name}_vel")
        effort = parse_float(row, f"{joint_name}_effort")

        if not math.isnan(position):
            positions.append(position)

            if joint_index in HIP_PITCH_INDICES:
                if position <= -1.565 or position >= 1.565:
                    limit_hits += 1
            elif joint_index in KNEE_PITCH_INDICES:
                if position <= -2.195 or position >= 0.195:
                    limit_hits += 1

        if not math.isnan(target):
            desired.append(target)

        if not math.isnan(position) and not math.isnan(target):
            errors.append(target - position)

        if not math.isnan(velocity):
            velocities.append(velocity)

        if not math.isnan(effort):
            efforts.append(effort)

    if not positions:
        return None

    rms_error = math.nan
    mean_error = math.nan
    max_abs_error = math.nan
    if errors:
        mean_error = sum(errors) / len(errors)
        rms_error = math.sqrt(sum(error * error for error in errors) / len(errors))
        max_abs_error = max(abs(error) for error in errors)

    mean_desired = math.nan
    if desired:
        mean_desired = sum(desired) / len(desired)

    mean_effort = math.nan
    max_abs_effort = math.nan
    if efforts:
        mean_effort = sum(efforts) / len(efforts)
        max_abs_effort = max(abs(effort) for effort in efforts)

    return {
        "joint": joint_name,
        "mean_pos": sum(positions) / len(positions),
        "mean_des": mean_desired,
        "mean_err": mean_error,
        "rms_err": rms_error,
        "max_abs_err": max_abs_error,
        "min_pos": min(positions),
        "max_pos": max(positions),
        "max_abs_vel": max(abs(velocity) for velocity in velocities) if velocities else math.nan,
        "mean_effort": mean_effort,
        "max_abs_effort": max_abs_effort,
        "limit_percent": 100.0 * limit_hits / len(positions),
    }


def format_value(value):
    if math.isnan(value):
        return "nan"
    return f"{value:.3f}"


def main():
    parser = argparse.ArgumentParser(
        description="Summarize quadruped joint angle CSV logs."
    )
    parser.add_argument("csv_path")
    args = parser.parse_args()

    with open(args.csv_path, newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    if not rows:
        print("No rows found.")
        return

    start_time = rows[0].get("time_sec", "")
    end_time = rows[-1].get("time_sec", "")
    print(f"samples: {len(rows)}")
    print(f"time: {start_time} -> {end_time} s")
    print()

    columns = [
        "joint",
        "mean_pos",
        "mean_des",
        "mean_err",
        "rms_err",
        "max_abs_err",
        "min_pos",
        "max_pos",
        "max_abs_vel",
        "mean_effort",
        "max_abs_effort",
        "limit_percent",
    ]
    widths = [18, 9, 9, 9, 9, 11, 9, 9, 11, 11, 14, 13]
    print(" ".join(name.rjust(width) for name, width in zip(columns, widths)))

    for index, joint_name in enumerate(JOINT_ORDER):
        summary = summarize_joint(rows, joint_name, index)
        if summary is None:
            continue

        values = [
            summary["joint"],
            format_value(summary["mean_pos"]),
            format_value(summary["mean_des"]),
            format_value(summary["mean_err"]),
            format_value(summary["rms_err"]),
            format_value(summary["max_abs_err"]),
            format_value(summary["min_pos"]),
            format_value(summary["max_pos"]),
            format_value(summary["max_abs_vel"]),
            format_value(summary["mean_effort"]),
            format_value(summary["max_abs_effort"]),
            f"{summary['limit_percent']:.1f}%",
        ]
        print(" ".join(value.rjust(width) for value, width in zip(values, widths)))

    print()
    debug_names = [
        "mode",
        "phase",
        "max_leg_error",
        "max_s",
        "max_effort",
        "stand_fraction",
        "cmd_vx",
        "cmd_vy",
        "cmd_wz",
        "cmd_age",
    ]
    for debug_name in debug_names:
        values = [
            parse_float(row, debug_name)
            for row in rows
            if row.get(debug_name, "") != ""
        ]
        values = [value for value in values if not math.isnan(value)]
        if not values:
            continue
        mean_value = sum(values) / len(values)
        print(
            f"{debug_name}: "
            f"min={min(values):.3f}, mean={mean_value:.3f}, "
            f"max={max(values):.3f}, last={values[-1]:.3f}"
        )


if __name__ == "__main__":
    main()
