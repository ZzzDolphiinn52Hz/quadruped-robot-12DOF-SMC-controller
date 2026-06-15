"""Controller test for quadruped: 4 legs x 3 DOF = 12 motors.

Leg structure for each leg:
J1 hip_yaw -> L1 connector -> J2 hip_pitch -> L2 thigh -> J3 knee_pitch -> L3 shank -> foot.
"""

from controller import Robot
import math

robot = Robot()
TIME_STEP = int(robot.getBasicTimeStep())

legs = ["FL", "FR", "RL", "RR"]
joint_suffixes = ["hip_yaw", "hip_pitch", "knee_pitch"]

joint_names = [f"{leg}_{joint}" for leg in legs for joint in joint_suffixes]

motors = {}
sensors = {}

for name in joint_names:
    motor = robot.getDevice(name)
    sensor = robot.getDevice(name + "_sensor")
    sensor.enable(TIME_STEP)

    motor.setVelocity(2.0)
    motor.setPosition(0.0)

    motors[name] = motor
    sensors[name] = sensor

# Trot phase: FL + RR same phase, FR + RL opposite phase.
phase = {
    "FL": 0.0,
    "RR": 0.0,
    "FR": math.pi,
    "RL": math.pi,
}

# side sign: left = +1, right = -1. Used only to make yaw motion visually symmetric.
side_sign = {
    "FL": 1.0,
    "RL": 1.0,
    "FR": -1.0,
    "RR": -1.0,
}

while robot.step(TIME_STEP) != -1:
    t = robot.getTime()
    
    # 1. TẦN SỐ: Giảm từ 0.35 xuống 0.2 để đi chậm lại
    f = 0.2 
    w = 2.0 * math.pi * f

    for leg in legs:
        ph = phase[leg]
        s = side_sign[leg]

        # 2. BIÊN ĐỘ (Amplitude)
        
        # J1: hip yaw (Lắc ngang) - Cho bằng 0 hoặc cực nhỏ để tránh robot bị ngoáy mông gây mất trụ
        q_yaw = s * 0.05 * math.sin(w * t + ph) 

        # J2: hip pitch (Vung chân tới lui) - Quyết định độ dài bước. 
        
        q_hip = 0.5 * math.sin(w * t + ph + math.pi / 2.0)

        # J3: knee pitch (Gập đầu gối) - Quyết định độ cao nhấc chân.
        # -0.8 là góc đứng (offset) thấp hơn một chút để hạ thấp trọng tâm robot cho vững.
        # Biên độ 0.15 giúp nhấc chân vừa đủ qua mặt đất.
        q_knee = -0.8 + 0.15 * math.sin(w * t + ph)

        motors[f"{leg}_hip_yaw"].setPosition(q_yaw)
        motors[f"{leg}_hip_pitch"].setPosition(q_hip)
        motors[f"{leg}_knee_pitch"].setPosition(q_knee)


    if int(t) != int(t - TIME_STEP / 1000.0):
        print(
            "t=%.2f | FL yaw=%.3f hip=%.3f knee=%.3f | FR yaw=%.3f hip=%.3f knee=%.3f"
            % (
                t,
                sensors["FL_hip_yaw"].getValue(),
                sensors["FL_hip_pitch"].getValue(),
                sensors["FL_knee_pitch"].getValue(),
                sensors["FR_hip_yaw"].getValue(),
                sensors["FR_hip_pitch"].getValue(),
                sensors["FR_knee_pitch"].getValue(),
            )
        )
