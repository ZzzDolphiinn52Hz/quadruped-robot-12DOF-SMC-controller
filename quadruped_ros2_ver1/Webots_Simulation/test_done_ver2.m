clc; clear; close all;
%% =========================================================
%  1) THAM SỐ QUỸ ĐẠO VÀ DÁNG ĐI
%  =========================================================
params.fp     = 1.0;          % Tần số bước [Hz]
params.T      = 1/params.fp;  % Chu kỳ bước Tp [s]

params.beta_t = 0.60;         % Duty factor theo thời gian
params.beta_u = 0.60;         % Duty factor trong miền tham số Bezier

params.d      = 0.08;         % Chiều dài bước [m]
params.h      = 0.04;         % Chiều cao bước [m]
params.theta  = 0;            % Hướng đi [rad], 0 = đi thẳng theo trục x

params.smooth_phase = true;   % true: làm mượt u(t) cho SMC/FTSMC

% Làm mượt vùng nối chu kỳ.
% 0   = không làm mượt, giống Eq. (20)
% 0.5 = mượt vừa
% 0.7 = mượt hơn, thường đẹp hơn cho SMC/FTSMC
params.seam_smooth_ratio = 0.7;
%% =========================================================
%  BODY CONTROLLER GAINS
%  =========================================================
body_gain.kx = 1.5;
body_gain.ky = 1.5;
body_gain.ktheta = 3.0;

% Giới hạn vận tốc thân
body_gain.v_max = 0.25;      % [m/s]
body_gain.w_max = 1.0;       % [rad/s]
%% =========================================================
%  2) VỊ TRÍ TRUNG TÂM P3 CỦA 4 CHÂN TRONG BODY FRAME
%  =========================================================
P3.FL = [ 0.18,  0.08, -0.25];
P3.FR = [ 0.18, -0.08, -0.25];
P3.RL = [-0.18,  0.08, -0.25];
P3.RR = [-0.18, -0.08, -0.25];

%% =========================================================
%  3) PHA DÁNG ĐI TROT
%  FL đi cùng RR, FR đi cùng RL
%  =========================================================
phase.FL = 0.0;
phase.RR = 0.0;
phase.FR = 0.5;
phase.RL = 0.5;

%% =========================================================
%  4) THỜI GIAN MÔ PHỎNG
%  =========================================================
dt = 0.005;
t = (0:dt:2*params.T)';

%% =========================================================
%  5) SINH QUỸ ĐẠO CHO 4 CHÂN
%  =========================================================
%% =========================================================
%  BODY REFERENCE AND CURRENT BODY STATE
%  =========================================================

body_state.px = 0.0;
body_state.py = 0.0;
body_state.theta = 0.0;

body_ref.pxd = 0.5;      % muốn thân đi tới x = 0.5 m
body_ref.pyd = 0.0;      % giữ y = 0
body_ref.vxd = 0.10;     % vận tốc feed-forward theo x
body_ref.vyd = 0.0;

% body_ref.pxd = 0.5;      % đi chéo
% body_ref.pyd = 0.5;
% body_ref.vxd = 0.10;
% body_ref.vyd = 0.10;

fprintf('\n===== BODY REF CHECK =====\n');
fprintf('pxd = %.4f\n', body_ref.pxd);
fprintf('pyd = %.4f\n', body_ref.pyd);
fprintf('vxd = %.4f\n', body_ref.vxd);
fprintf('vyd = %.4f\n', body_ref.vyd);

body_cmd = planar_body_controller(body_state, body_ref, body_gain);

legs = {'FL','FR','RL','RR'};
traj = struct();
leg_param_log = struct();

fprintf('\n===== LEG STEP PARAMETERS =====\n');

for k = 1:numel(legs)
    leg = legs{k};

    % Tính d và theta riêng cho từng chân từ body controller
    params_leg = body_velocity_to_leg_params(body_cmd, P3.(leg), params);

    % Lưu lại để kiểm tra
    leg_param_log.(leg) = params_leg;

    fprintf('%s: d = %.4f m, theta = %.4f rad = %.2f deg, speed = %.4f m/s\n', ...
        leg, params_leg.d, params_leg.theta, ...
        rad2deg(params_leg.theta), params_leg.speed_leg);

    % Sinh quỹ đạo Bézier cho chân đó
    traj.(leg) = generate_matrix_traj(t, P3.(leg), phase.(leg), params_leg);
end

%% =========================================================
%  5.1) TẠO THAM CHIẾU KHỚP qd, qd_dot, qd_ddot TỪ IK
%  =========================================================
robot_geom.L_thigh = 0.16;
robot_geom.L_shank = 0.16;
robot_geom.knee_direction = 1;

joint_ref = generate_joint_references(t, traj, P3, robot_geom);

% Vẽ góc khớp mong muốn của chân FL
figure('Name','FL Desired Joint References','Color','w');

subplot(3,1,1);
plot(t, joint_ref.FL.qd, 'LineWidth', 1.5);
grid on;
ylabel('q_d [rad]');
title('FL desired joint angles');
legend('q1d','q2d','q3d');

subplot(3,1,2);
plot(t, joint_ref.FL.qd_dot, 'LineWidth', 1.5);
grid on;
ylabel('qdot_d [rad/s]');
title('FL desired joint velocities');
legend('q1dot_d','q2dot_d','q3dot_d');

subplot(3,1,3);
plot(t, joint_ref.FL.qd_ddot, 'LineWidth', 1.5);
grid on;
ylabel('qddot_d [rad/s^2]');
xlabel('time [s]');
title('FL desired joint accelerations');
legend('q1ddot_d','q2ddot_d','q3ddot_d');

%% =========================================================
%  5.2) KIỂM TRA SAI SỐ IK/FK
%  =========================================================
check_ik_fk_error(t, traj, P3, joint_ref, robot_geom);

%% =========================================================
%  5.3) SMC JOINT TRACKING
%  =========================================================
smc.lambda = [18, 18, 18];      % hệ số mặt trượt
smc.k      = [30, 30, 30];      % gain switching
smc.phi    = [0.12, 0.12, 0.12];% boundary layer để giảm chattering
smc.u_max  = [150, 150, 150];   % giới hạn điều khiển

% Mô phỏng SMC cho 4 chân
smc_result = simulate_smc_all_legs(t, joint_ref, smc);

% Vẽ kết quả bám của chân FL
plot_smc_tracking_result(t, smc_result, 'FL');

% Lưu ra workspace nếu cần dùng tiếp
assignin('base', 'smc_result', smc_result);

%% =========================================================
%  5.4) ANIMATION USING ACTUAL q FROM SMC
%  =========================================================
anim_opts.frame_skip      = 2;
anim_opts.pause_time      = 0.01;
anim_opts.trail_length    = 250;

anim_opts.body_length     = 0.42;
anim_opts.body_width      = 0.20;
anim_opts.body_height     = 0.08;

anim_opts.body_z          = abs(P3.FL(3));
anim_opts.body_box_offset = 0.03;

anim_opts.use_body_motion = true;
anim_opts.use_yaw_motion  = false;

animate_quadruped_smc(t, smc_result, P3, body_cmd, robot_geom, anim_opts);

%% =========================================================
%  5.5) CHECK FOOT ERROR AFTER SMC
%  =========================================================
check_smc_foot_tracking_error(t, traj, smc_result, P3, robot_geom);

%% =========================================================
%  11) ANIMATION QUADRUPED ROBOT
%  =========================================================
anim_opts.frame_skip      = 2;       % tăng lên 4 hoặc 5 nếu máy chậm
anim_opts.pause_time      = 0.01;
anim_opts.trail_length    = 250;     % số điểm vẽ vết quỹ đạo bàn chân

anim_opts.body_length     = 0.42;    % [m]
anim_opts.body_width      = 0.20;    % [m]
anim_opts.body_height     = 0.08;    % [m]

% Thông số hình học chân cho IK/FK
% Bạn thay lại theo đúng robot của bạn nếu có số liệu thật
anim_opts.L_thigh = 0.16;      % chiều dài đùi [m]
anim_opts.L_shank = 0.16;      % chiều dài cẳng chân [m]

% 1 hoặc -1 để đổi kiểu gập gối nếu chân bị gập ngược
anim_opts.knee_direction = 1;

anim_opts.body_z          = abs(P3.FL(3));   % nếu P3.z = -0.25 thì thân cao 0.25 m
anim_opts.body_box_offset = 0.03;            % nâng hộp thân lên một chút

anim_opts.use_body_motion = true;    % true: thân robot di chuyển theo body_cmd
anim_opts.use_yaw_motion  = false;    % true: thân robot quay theo uaw

% animate_quadruped_bezier(t, traj, P3, body_cmd, anim_opts);

%% =========================================================
%  6) VẼ QUỸ ĐẠO 3D CỦA 4 CHÂN
%  =========================================================
figure('Name','3D Foot Trajectories - 4 Legs','Color','w');
hold on; grid on; axis equal;

hLeg = gobjects(numel(legs),1);

for k = 1:numel(legs)
    leg = legs{k};
    pos = traj.(leg).pos;

    hLeg(k) = plot3(pos(:,1), pos(:,2), pos(:,3), ...
        'LineWidth', 2);
end

for k = 1:numel(legs)
    leg = legs{k};
    c = P3.(leg);

    plot3(c(1), c(2), c(3), 'ko', ...
        'MarkerFaceColor','k', ...
        'HandleVisibility','off');

    text(c(1), c(2), c(3), ['  P3 ' leg], ...
        'FontWeight','bold');
end

xlabel('x [m]');
ylabel('y [m]');
zlabel('z [m]');
title('Bezier Foot Trajectories for 4 Legs - Trot Gait');
legend(hLeg, legs, 'Location','best');
view(35,25);

%% =========================================================
%  7) VẼ MẶT PHẲNG x-z CHO TỪNG CHÂN
%  =========================================================
figure('Name','Foot Trajectories in x-z Plane','Color','w');

for k = 1:numel(legs)
    leg = legs{k};

    pos  = traj.(leg).pos;
    Pfit = traj.(leg).Pfit;

    subplot(2,2,k);
    hold on; grid on; axis equal;

    plot(pos(:,1), pos(:,3), 'b', 'LineWidth', 2);
    plot(Pfit(:,1), Pfit(:,3), 'r*', ...
        'MarkerSize', 8, 'LineWidth', 1.5);

    % Đánh dấu đoạn support theo tài liệu: P2 -> P3 -> P4
    plot(Pfit(3:5,1), Pfit(3:5,3), 'k--', ...
        'LineWidth', 1.0);

    for i = 1:7
        text(Pfit(i,1), Pfit(i,3), sprintf('  P%d', i-1), ...
            'FontSize', 9, 'FontWeight','bold');
    end

    xlabel('x [m]');
    ylabel('z [m]');
    title([leg ' Foot Trajectory in x-z Plane']);
    legend('Bezier trajectory','P0...P6','Support P2-P4', ...
        'Location','best');
end

%% =========================================================
%  8) VỊ TRÍ, VẬN TỐC, GIA TỐC CỦA CHÂN FL
%  =========================================================
leg = 'FL';

figure('Name','FL Position, Velocity and Acceleration','Color','w');

subplot(3,1,1);
plot(t, traj.(leg).pos(:,1), 'r', ...
     t, traj.(leg).pos(:,2), 'g', ...
     t, traj.(leg).pos(:,3), 'b', 'LineWidth', 1.5);
grid on;
ylabel('Position [m]');
title('FL Foot Position');
legend('x','y','z');

subplot(3,1,2);
plot(t, traj.(leg).vel(:,1), 'r', ...
     t, traj.(leg).vel(:,2), 'g', ...
     t, traj.(leg).vel(:,3), 'b', 'LineWidth', 1.5);
grid on;
ylabel('Velocity [m/s]');
title('FL Foot Velocity');
legend('Vx','Vy','Vz');

subplot(3,1,3);
plot(t, traj.(leg).acc(:,1), 'r', ...
     t, traj.(leg).acc(:,2), 'g', ...
     t, traj.(leg).acc(:,3), 'b', 'LineWidth', 1.5);
grid on;
ylabel('Acceleration [m/s^2]');
xlabel('time [s]');
title('FL Foot Acceleration');
legend('Ax','Ay','Az');

%% =========================================================
%  9) VẼ THAM SỐ u(t) CỦA 4 CHÂN
%  =========================================================
figure('Name','Bezier Parameter u(t)','Color','w');
hold on; grid on;

for k = 1:numel(legs)
    leg = legs{k};
    plot(t, traj.(leg).u, 'LineWidth', 1.5);
end

xlabel('time [s]');
ylabel('u');
title('Mapping from Normalized Time to Bezier Parameter u');
legend('FL','FR','RL','RR');

%% =========================================================
%  10) VẼ PHA xi(t) CỦA 4 CHÂN
%  =========================================================
figure('Name','Normalized Phase xi(t)','Color','w');
hold on; grid on;

for k = 1:numel(legs)
    leg = legs{k};
    plot(t, traj.(leg).xi, 'LineWidth', 1.5);
end

xlabel('time [s]');
ylabel('\xi = t/T_p');
title('Normalized Time Phase with Trot Offsets');
legend('FL','FR','RL','RR');

%% =========================================================
%  LOCAL FUNCTIONS
%  =========================================================

function out = generate_matrix_traj(t, P3, phase_offset, params)
    % Sinh quỹ đạo bàn chân bằng:
    % 1) P0...P6 theo Eq. (19)
    % 2) u(t) theo Eq. (20), hoặc u(t) làm mượt vùng nối chu kỳ
    % 3) Bezier bậc 6 dạng ma trận Eq. (16)
    % 4) Đạo hàm Eq. (17), (18)

    % Tạo các điểm fitting P0...P6
    [Pfit, u_pts] = generate_step_points(P3, params);

    % Tính trọng số W từ Pfit
    W = fit_bezier6_weights(Pfit, u_pts);

    % Kiểm tra đường cong có đi qua P0...P6 không
    [Pcheck, ~, ~] = bezier6_eval_all(W, u_pts);
    fit_error = max(max(abs(Pcheck - Pfit)));

    % Pha thời gian có cộng offset cho từng chân
    xi = mod(t/params.T + phase_offset, 1.0);

    % Ánh xạ xi -> u
    % Nếu smooth_phase = true: làm mượt vùng nối chu kỳ
    % Nếu smooth_phase = false: dùng đúng Eq. (20) tuyến tính từng đoạn
    if isfield(params, 'smooth_phase') && params.smooth_phase

        if isfield(params, 'seam_smooth_ratio')
            seam_smooth_ratio = params.seam_smooth_ratio;
        else
            seam_smooth_ratio = 0.7;
        end

        [u, du_dt, d2u_dt2] = phase_to_u_seam_smooth( ...
            xi, params.beta_t, params.beta_u, params.T, seam_smooth_ratio);

    else

        [u, du_dt, d2u_dt2] = phase_to_u_eq20( ...
            xi, params.beta_t, params.beta_u, params.T);

    end

    % Tính B(u), dB/du, d2B/du2
    [pos, dB_du, d2B_du2] = bezier6_eval_all(W, u);

    % Chain rule:
    % dB/dt = dB/du * du/dt
    % d2B/dt2 = d2B/du2 * (du/dt)^2 + dB/du * d2u/dt2
    du_dt_mat   = repmat(du_dt, 1, 3);
    d2u_dt2_mat = repmat(d2u_dt2, 1, 3);

    vel = dB_du .* du_dt_mat;
    acc = d2B_du2 .* (du_dt_mat.^2) + dB_du .* d2u_dt2_mat;

    out.pos       = pos;
    out.vel       = vel;
    out.acc       = acc;
    out.u         = u;
    out.xi        = xi;
    out.Pfit      = Pfit;
    out.u_pts     = u_pts;
    out.W         = W;
    out.fit_error = fit_error;
end

function [P, u_pts] = generate_step_points(P3, params)
    % Tạo P0...P6 đúng theo Eq. (19) của tài liệu.
    %
    % dx = 0.7*d*cos(theta)
    % dy = 0.7*d*sin(theta)
    %
    % Support phase: P2 -> P3 -> P4
    % Swing phase  : P4 -> P5 -> P6/P0 -> P1 -> P2

    d  = params.d;
    h  = params.h;
    th = params.theta;

    beta_u = params.beta_u;

    dx = 0.7 * d * cos(th);
    dy = 0.7 * d * sin(th);

    P0 = [P3(1),             P3(2),             P3(3) + h        ];

    P1 = [P3(1) + dx*(4/5),  P3(2) + dy*(4/5),  P3(3) + h*(3/5)  ];

    P2 = [P3(1) + dx*(5/5),  P3(2) + dy*(5/5),  P3(3) + h*(1/5)  ];

    P4 = [P3(1) - dx*(5/5),  P3(2) - dy*(5/5),  P3(3) + h*(1/5)  ];

    P5 = [P3(1) - dx*(4/5),  P3(2) - dy*(4/5),  P3(3) + h*(3/5)  ];

    P6 = P0;

    P = [P0;
         P1;
         P2;
         P3;
         P4;
         P5;
         P6];

    % Chọn u_i để support P2 -> P4 chiếm beta_u trong miền u.
    %
    % Với beta_u = 0.6:
    % u0 = 0
    % u1 = 0.1
    % u2 = 0.2
    % u3 = 0.5
    % u4 = 0.8
    % u5 = 0.9
    % u6 = 1

    u0 = 0;
    u2 = (1 - beta_u)/2;
    u3 = 0.5;
    u4 = (1 + beta_u)/2;
    u6 = 1;

    u1 = (u0 + u2)/2;
    u5 = (u4 + u6)/2;

    u_pts = [u0;
             u1;
             u2;
             u3;
             u4;
             u5;
             u6];
end

function [u, du_dt, d2u_dt2] = phase_to_u_eq20(xi, beta_t, beta_u, T)
    % Eq. (20): ánh xạ xi = t/Tp sang tham số Bezier u.
    %
    % u(xi) gồm 3 đoạn:
    % 1) 0 <= xi < (1-beta_t)/2
    % 2) (1-beta_t)/2 <= xi <= (1+beta_t)/2
    % 3) (1+beta_t)/2 < xi <= 1

    if beta_t <= 0 || beta_t >= 1
        error('beta_t phải nằm trong khoảng (0, 1).');
    end

    if beta_u <= 0 || beta_u >= 1
        error('beta_u phải nằm trong khoảng (0, 1).');
    end

    xi = mod(xi, 1);

    u = zeros(size(xi));
    du_dxi = zeros(size(xi));
    d2u_dxi2 = zeros(size(xi));

    xi1 = (1 - beta_t)/2;
    xi2 = (1 + beta_t)/2;

    idx1 = xi < xi1;
    idx2 = xi >= xi1 & xi <= xi2;
    idx3 = xi > xi2;

    % Đoạn 1
    slope13 = (beta_u - 1) / (beta_t - 1);

    u(idx1) = xi(idx1) .* slope13;
    du_dxi(idx1) = slope13;

    % Đoạn 2
    slope2 = beta_u / beta_t;

    u(idx2) = beta_u .* (2*xi(idx2) - 1) ./ (2*beta_t) + 1/2;
    du_dxi(idx2) = slope2;

    % Đoạn 3
    u(idx3) = beta_u/2 ...
        - ((beta_u - 1) .* (beta_t - 2*xi(idx3) + 1)) ./ ...
          (2*(beta_t - 1)) ...
        + 1/2;

    du_dxi(idx3) = slope13;

    % Vì xi = t/Tp:
    % du/dt = du/dxi * dxi/dt = du/dxi * 1/Tp
    du_dt = du_dxi / T;

    % Eq. (20) là tuyến tính từng đoạn nên d2u/dt2 = 0 trong từng đoạn.
    % Tại điểm chuyển đoạn, đạo hàm có thể đổi đột ngột nếu beta_t ~= beta_u.
    d2u_dt2 = d2u_dxi2 / (T^2);
end

function [u, du_dt, d2u_dt2] = phase_to_u_seam_smooth(xi, beta_t, beta_u, T, smooth_ratio)
    % Làm mượt ánh xạ u(t) ở vùng nối chu kỳ.
    %
    % Ý tưởng:
    % - Phần lớn chu kỳ vẫn giữ đúng Eq. (20).
    % - Chỉ làm mượt gần xi = 0 và xi = 1.
    %
    % Như vậy:
    % - Giảm gãy vận tốc/gia tốc tại điểm lặp chu kỳ.
    % - Không làm méo toàn bộ u(t) như smooth_quintic toàn đoạn.

    if beta_t <= 0 || beta_t >= 1
        error('beta_t phải nằm trong khoảng (0, 1).');
    end

    if beta_u <= 0 || beta_u >= 1
        error('beta_u phải nằm trong khoảng (0, 1).');
    end

    if nargin < 5
        smooth_ratio = 0.7;
    end

    smooth_ratio = max(0, min(0.95, smooth_ratio));

    xi = mod(xi, 1);

    % Lấy Eq. (20) làm nền
    [u, du_dt_base, ~] = phase_to_u_eq20(xi, beta_t, beta_u, T);

    du_dxi = du_dt_base * T;
    d2u_dxi2 = zeros(size(xi));

    % Các mốc của Eq. (20)
    xi1 = (1 - beta_t)/2;
    xi2 = (1 + beta_t)/2;

    % Slope đoạn đầu/cuối của Eq. (20)
    m13 = (beta_u - 1) / (beta_t - 1);

    % Độ rộng vùng làm mượt.
    % Vùng này nằm trong swing đầu/cuối, không đụng vào support.
    min_swing_part = min(xi1, 1 - xi2);
    delta = smooth_ratio * min_swing_part;

    if delta <= eps
        du_dt = du_dxi / T;
        d2u_dt2 = d2u_dxi2 / (T^2);
        return;
    end

    %% =====================================================
    %  Vùng đầu chu kỳ: xi = 0 -> delta
    %
    %  Điều kiện:
    %  tại xi=0:
    %     u = 0, du/dxi = 0, d2u/dxi2 = 0
    %
    %  tại xi=delta:
    %     u = m13*delta, du/dxi = m13, d2u/dxi2 = 0
    %  =====================================================
    idx_start = xi >= 0 & xi < delta;

    if any(idx_start)
        x0 = 0;
        x1 = delta;

        u0 = 0;
        v0 = 0;
        a0 = 0;

        u1 = m13 * delta;
        v1 = m13;
        a1 = 0;

        [u_val, du_val, d2u_val] = quintic_hermite_segment( ...
            xi(idx_start), x0, x1, ...
            u0, v0, a0, ...
            u1, v1, a1);

        u(idx_start) = u_val;
        du_dxi(idx_start) = du_val;
        d2u_dxi2(idx_start) = d2u_val;
    end

    %% =====================================================
    %  Vùng cuối chu kỳ: xi = 1-delta -> 1
    %
    %  Điều kiện:
    %  tại xi=1-delta:
    %     u = 1 - m13*delta, du/dxi = m13, d2u/dxi2 = 0
    %
    %  tại xi=1:
    %     u = 1, du/dxi = 0, d2u/dxi2 = 0
    %  =====================================================
    idx_end = xi > (1 - delta) & xi < 1;

    if any(idx_end)
        x0 = 1 - delta;
        x1 = 1;

        u0 = 1 - m13 * delta;
        v0 = m13;
        a0 = 0;

        u1 = 1;
        v1 = 0;
        a1 = 0;

        [u_val, du_val, d2u_val] = quintic_hermite_segment( ...
            xi(idx_end), x0, x1, ...
            u0, v0, a0, ...
            u1, v1, a1);

        u(idx_end) = u_val;
        du_dxi(idx_end) = du_val;
        d2u_dxi2(idx_end) = d2u_val;
    end

    % Đổi đạo hàm theo xi sang đạo hàm theo thời gian
    du_dt = du_dxi / T;
    d2u_dt2 = d2u_dxi2 / (T^2);
end

function [p, v, a] = quintic_hermite_segment(x, x0, x1, p0, v0, a0, p1, v1, a1)
    % Nội suy Hermite bậc 5 giữa hai điểm.
    %
    % p0, v0, a0: vị trí, đạo hàm bậc 1, đạo hàm bậc 2 tại x0
    % p1, v1, a1: vị trí, đạo hàm bậc 1, đạo hàm bậc 2 tại x1
    %
    % Output:
    % p = giá trị nội suy
    % v = dp/dx
    % a = d2p/dx2

    L = x1 - x0;

    if L <= 0
        error('x1 phải lớn hơn x0.');
    end

    s = (x - x0) / L;
    s = max(0, min(1, s));

    % Đổi đạo hàm theo x sang đạo hàm theo s
    V0 = v0 * L;
    V1 = v1 * L;
    A0 = a0 * L^2;
    A1 = a1 * L^2;

    c0 = p0;
    c1 = V0;
    c2 = A0 / 2;

    c3 = 10*(p1 - p0) - 6*V0 - 4*V1 - 1.5*A0 + 0.5*A1;
    c4 = -15*(p1 - p0) + 8*V0 + 7*V1 + 1.5*A0 - A1;
    c5 = 6*(p1 - p0) - 3*V0 - 3*V1 - 0.5*A0 + 0.5*A1;

    p = c0 + c1*s + c2*s.^2 + c3*s.^3 + c4*s.^4 + c5*s.^5;

    dp_ds = c1 + 2*c2*s + 3*c3*s.^2 + 4*c4*s.^3 + 5*c5*s.^4;

    d2p_ds2 = 2*c2 + 6*c3*s + 12*c4*s.^2 + 20*c5*s.^3;

    % Đổi lại đạo hàm theo x
    v = dp_ds / L;
    a = d2p_ds2 / (L^2);
end

function W = fit_bezier6_weights(P, u_pts)
    % Tính ma trận trọng số W theo Eq. (15).
    %
    % B(u) = [1 u u^2 ... u^6] * M * W
    %
    % Tại các điểm fitting:
    % P = T * M * W
    %
    % Suy ra:
    % W = M^(-1) * T^(-1) * P

    M6 = bezier6_matrix();

    u = u_pts(:);

    Tmat = [ones(size(u)), ...
            u, ...
            u.^2, ...
            u.^3, ...
            u.^4, ...
            u.^5, ...
            u.^6];

    % Dùng backslash, không dùng inv trực tiếp
    C = Tmat \ P;
    W = M6 \ C;
end

function [p, dp_du, ddp_du2] = bezier6_eval_all(W, u)
    % Tính:
    % p        = B(u)
    % dp_du    = dB/du
    % ddp_du2  = d2B/du2
    %
    % Theo Eq. (16), (17), (18).

    u = u(:);

    M6 = bezier6_matrix();
    M5 = bezier5_matrix();
    M4 = bezier4_matrix();

    U6 = [ones(size(u)), ...
          u, ...
          u.^2, ...
          u.^3, ...
          u.^4, ...
          u.^5, ...
          u.^6];

    U5 = [ones(size(u)), ...
          u, ...
          u.^2, ...
          u.^3, ...
          u.^4, ...
          u.^5];

    U4 = [ones(size(u)), ...
          u, ...
          u.^2, ...
          u.^3, ...
          u.^4];

    % Eq. (16)
    p = U6 * M6 * W;

    % Eq. (17):
    % W'_i = 6(W_{i+1} - W_i)
    Wp = 6 * (W(2:end,:) - W(1:end-1,:));

    dp_du = U5 * M5 * Wp;

    % Eq. (18):
    % W''_i = 5(W'_{i+1} - W'_i)
    Wpp = 5 * (Wp(2:end,:) - Wp(1:end-1,:));

    ddp_du2 = U4 * M4 * Wpp;
end

function M = bezier6_matrix()
    % Ma trận M cho Bezier bậc 6 theo Eq. (16)

    M = [  1,   0,    0,    0,   0,   0,  0;
          -6,   6,    0,    0,   0,   0,  0;
          15, -30,   15,    0,   0,   0,  0;
         -20,  60,  -60,   20,   0,   0,  0;
          15, -60,   90,  -60,  15,   0,  0;
          -6,  30,  -60,   60, -30,   6,  0;
           1,  -6,   15,  -20,  15,  -6,  1 ];
end

function M = bezier5_matrix()
    % Ma trận M cho Bezier bậc 5, dùng cho đạo hàm bậc nhất Eq. (17)

    M = [  1,   0,    0,    0,   0,  0;
          -5,   5,    0,    0,   0,  0;
          10, -20,   10,    0,   0,  0;
         -10,  30,  -30,   10,   0,  0;
           5, -20,   30,  -20,   5,  0;
          -1,   5,  -10,   10,  -5,  1 ];
end

function M = bezier4_matrix()
    % Ma trận M cho Bezier bậc 4, dùng cho đạo hàm bậc hai Eq. (18)

    M = [  1,   0,    0,   0,  0;
          -4,   4,    0,   0,  0;
           6, -12,    6,   0,  0;
          -4,  12,  -12,   4,  0;
           1,  -4,    6,  -4,  1 ];
end

function body_cmd = planar_body_controller(body_state, body_ref, gain)
    % body_state.px = 0.0;
    % body_state.py = 0.0;
    % body_state.theta = 0.0;
    % 
    % body_ref.pxd = 0.5;
    % body_ref.pyd = 0.5;
    % body_ref.vxd = 0.10;
    % body_ref.vyd = 0.10;

    px = body_state.px;
    py = body_state.py;
    theta = body_state.theta;

    pxd = body_ref.pxd;
    pyd = body_ref.pyd;
    vxd = body_ref.vxd;
    vyd = body_ref.vyd;

    kx = gain.kx;
    ky = gain.ky;
    ktheta = gain.ktheta;

    % Sai số vị trí thân
    ex = pxd - px;
    ey = pyd - py;

    % Auxiliary control trong hệ quán tính
    uax = vxd + kx * ex;
    uay = vyd + ky * ey;

    % Giới hạn vận tốc tuyến tính
    v_norm = sqrt(uax^2 + uay^2);
    if v_norm > gain.v_max
        scale = gain.v_max / v_norm;
        uax = uax * scale;
        uay = uay * scale;
    end

    % Hướng thân mong muốn
    if sqrt(uax^2 + uay^2) > 1e-6
        theta_d = atan2(uay, uax);
    else
        theta_d = theta;
    end

    % Sai số góc, có wrap về [-pi, pi]
    e_theta = wrap_to_pi(theta_d - theta);

    % Auxiliary yaw control
    uaw = ktheta * e_theta;

    % Giới hạn vận tốc quay
    uaw = max(min(uaw, gain.w_max), -gain.w_max);

    % Feedback linearization:
    % đổi từ vận tốc hệ quán tính sang vận tốc trong hệ robot
    vrx =  cos(theta) * uax + sin(theta) * uay;
    vry = -sin(theta) * uax + cos(theta) * uay;
    wr  = uaw;

    body_cmd.uax = uax;
    body_cmd.uay = uay;
    body_cmd.uaw = uaw;

    body_cmd.vrx = vrx;
    body_cmd.vry = vry;
    body_cmd.wr  = wr;

    body_cmd.theta_d = theta_d;
    body_cmd.ex = ex;
    body_cmd.ey = ey;
    body_cmd.e_theta = e_theta;
    fprintf('\n===== BODY COMMAND =====\n');
    fprintf('uax = %.4f m/s\n', body_cmd.uax);
    fprintf('uay = %.4f m/s\n', body_cmd.uay);
    fprintf('uaw = %.4f rad/s\n', body_cmd.uaw);
    fprintf('vrx = %.4f m/s\n', body_cmd.vrx);
    fprintf('vry = %.4f m/s\n', body_cmd.vry);
    fprintf('wr  = %.4f rad/s\n', body_cmd.wr);
    fprintf('theta_d = %.4f rad = %.2f deg\n', ...
    body_cmd.theta_d, rad2deg(body_cmd.theta_d));
end

function ang = wrap_to_pi(ang)
    ang = atan2(sin(ang), cos(ang));
end

function leg_params = body_velocity_to_leg_params(body_cmd, P3_leg, params)
    % Chuyển vận tốc thân thành chiều dài bước và hướng bước cho từng chân.
    %
    % P3_leg: vị trí trung tâm bàn chân trong body frame [x y z]
    % body_cmd.vrx, body_cmd.vry, body_cmd.wr: vận tốc thân trong body frame

    vrx = body_cmd.vrx;
    vry = body_cmd.vry;
    wr  = body_cmd.wr;

    x_leg = P3_leg(1);
    y_leg = P3_leg(2);

    % Thành phần vận tốc do thân quay yaw
    v_yaw_x = -wr * y_leg;
    v_yaw_y =  wr * x_leg;

    % Vận tốc tương đối mong muốn tại chân
    vx_leg = vrx + v_yaw_x;
    vy_leg = vry + v_yaw_y;

    speed_leg = sqrt(vx_leg^2 + vy_leg^2);

    % Copy tham số gốc
    leg_params = params;

    % Chiều dài bước xấp xỉ
    leg_params.d = speed_leg * params.T;

    % Giới hạn chiều dài bước để không quá lớn hoặc quá nhỏ
    d_min = 0.00;
    d_max = 0.12;

    leg_params.d = max(min(leg_params.d, d_max), d_min);

    % Hướng bước
    if speed_leg > 1e-6
        leg_params.theta = atan2(vy_leg, vx_leg);
    else
        leg_params.theta = 0;
    end

    % Lưu thêm để kiểm tra
    leg_params.vx_leg = vx_leg;
    leg_params.vy_leg = vy_leg;
    leg_params.speed_leg = speed_leg;
end

function animate_quadruped_bezier(t, traj, P3, body_cmd, opt)
    % Animation quadruped robot dùng IK + FK thật:
    %
    % p_d(t) trong body frame
    %       -> IK tìm q_d
    %       -> FK tìm hip, knee, foot
    %       -> vẽ animation
    %
    % Mô hình chân giả định:
    % q1: hip ab/ad, quay quanh trục x
    % q2: hip pitch
    % q3: knee pitch

    if nargin < 5
        opt = struct();
    end

    opt = set_anim_default_options(opt);

    legs = {'FL','FR','RL','RR'};
    N = numel(t);

    % ------------------------------------------------------
    % 1) Tính chuyển động thân trong world frame
    % ------------------------------------------------------
    body_pos = zeros(N,3);
    body_yaw = zeros(N,1);

    for n = 1:N
        if opt.use_body_motion
            body_pos(n,1) = body_cmd.uax * t(n);
            body_pos(n,2) = body_cmd.uay * t(n);
        else
            body_pos(n,1) = 0;
            body_pos(n,2) = 0;
        end

        body_pos(n,3) = opt.body_z;

        if opt.use_yaw_motion
            body_yaw(n) = body_cmd.uaw * t(n);
        else
            body_yaw(n) = 0;
        end
    end

    % ------------------------------------------------------
    % 2) Precompute hip, knee, foot bằng IK + FK
    % ------------------------------------------------------
    hipW  = struct();
    kneeW = struct();
    footW = struct();
    qLog  = struct();

    geom.L_thigh = opt.L_thigh;
    geom.L_shank = opt.L_shank;
    geom.knee_direction = opt.knee_direction;

    for k = 1:numel(legs)
        leg = legs{k};

        hipW.(leg)  = zeros(N,3);
        kneeW.(leg) = zeros(N,3);
        footW.(leg) = zeros(N,3);
        qLog.(leg)  = zeros(N,3);
    end

    for n = 1:N
        for k = 1:numel(legs)
            leg = legs{k};

            % Foot desired trong body frame
            foot_body_des = traj.(leg).pos(n,:);

            % Hip attachment trong body frame
            hip_body = [P3.(leg)(1), P3.(leg)(2), 0];

            % Vector foot so với hip, vẫn trong body frame
            foot_rel_des = foot_body_des - hip_body;

            % IK: p_rel -> q
            q = leg_ik_3dof(foot_rel_des, geom);

            % FK: q -> hip_rel, knee_rel, foot_rel
            [hip_rel, knee_rel, foot_rel_fk] = leg_fk_3dof(q, geom);

            % Đưa các điểm trở lại body frame
            hip_body_fk  = hip_body + hip_rel;
            knee_body_fk = hip_body + knee_rel;
            foot_body_fk = hip_body + foot_rel_fk;

            % Đổi body frame -> world frame
            hipW.(leg)(n,:)  = body_to_world(hip_body_fk,  body_pos(n,:), body_yaw(n));
            kneeW.(leg)(n,:) = body_to_world(knee_body_fk, body_pos(n,:), body_yaw(n));
            footW.(leg)(n,:) = body_to_world(foot_body_fk, body_pos(n,:), body_yaw(n));

            qLog.(leg)(n,:) = q;
        end
    end

    % ------------------------------------------------------
    % 3) Chuẩn bị figure
    % ------------------------------------------------------
    figAnim = figure('Name','Quadruped Bezier Gait Animation with IK/FK','Color','w');
    axAnim = axes('Parent', figAnim);
    hold(axAnim, 'on');
    grid(axAnim, 'on');
    axis(axAnim, 'equal');
    
    xlabel(axAnim, 'X [m]');
    ylabel(axAnim, 'Y [m]');
    zlabel(axAnim, 'Z [m]');
    title(axAnim, 'Quadruped Animation - Bezier Gait + IK/FK');
    view(axAnim, 40, 25);

    allPts = body_pos;

    for k = 1:numel(legs)
        leg = legs{k};
        allPts = [allPts; hipW.(leg); kneeW.(leg); footW.(leg)]; %#ok<AGROW>
    end

    margin = 0.25;
    xlim([min(allPts(:,1))-margin, max(allPts(:,1))+margin]);
    ylim([min(allPts(:,2))-margin, max(allPts(:,2))+margin]);
    zlim([0, max(allPts(:,3)) + 0.25]);

    % Đường đi của thân
    plot3(body_pos(:,1), body_pos(:,2), body_pos(:,3), ...
        'k--', 'LineWidth', 1.2);

    % Đường mặt đất
    plot3([min(allPts(:,1))-margin, max(allPts(:,1))+margin], ...
          [0, 0], [0, 0], 'k:', 'LineWidth', 1.0);

    % ------------------------------------------------------
    % 4) Tạo body patch
    % ------------------------------------------------------
    body_center = body_pos(1,:) + [0, 0, opt.body_box_offset];

    [Vbody, Fbody] = body_box_vertices( ...
        body_center, body_yaw(1), ...
        opt.body_length, opt.body_width, opt.body_height);

    hBody = patch('Vertices', Vbody, ...
                  'Faces', Fbody, ...
                  'FaceColor', [0.35 0.65 1.0], ...
                  'FaceAlpha', 0.45, ...
                  'EdgeColor', [0.1 0.1 0.1], ...
                  'LineWidth', 1.2);

    % ------------------------------------------------------
    % 5) Tạo handle cho chân và trail
    % ------------------------------------------------------
    colorSet = lines(4);

    hLeg   = gobjects(4,1);
    hFoot  = gobjects(4,1);
    hTrail = gobjects(4,1);

    for k = 1:numel(legs)
        leg = legs{k};

        hTrail(k) = plot3(nan, nan, nan, ':', ...
            'Color', colorSet(k,:), ...
            'LineWidth', 1.2);

        hLeg(k) = plot3(nan, nan, nan, '-o', ...
            'Color', colorSet(k,:), ...
            'LineWidth', 2.5, ...
            'MarkerSize', 5, ...
            'MarkerFaceColor', colorSet(k,:));

        hFoot(k) = plot3(nan, nan, nan, 'o', ...
            'Color', colorSet(k,:), ...
            'MarkerSize', 7, ...
            'MarkerFaceColor', colorSet(k,:));

        text(hipW.(leg)(1,1), hipW.(leg)(1,2), hipW.(leg)(1,3), ...
            ['  ' leg], 'FontWeight','bold', 'Color', colorSet(k,:));
    end

    legend([hBody; hLeg], [{'Body'}, legs], 'Location','best');

    % ------------------------------------------------------
    % 6) Animation loop
    % ------------------------------------------------------
    for n = 1:opt.frame_skip:N

        % Update body
        body_center = body_pos(n,:) + [0, 0, opt.body_box_offset];

        [Vbody, ~] = body_box_vertices( ...
            body_center, body_yaw(n), ...
            opt.body_length, opt.body_width, opt.body_height);

        set(hBody, 'Vertices', Vbody);

        % Update từng chân
        for k = 1:numel(legs)
            leg = legs{k};

            hip  = hipW.(leg)(n,:);
            knee = kneeW.(leg)(n,:);
            foot = footW.(leg)(n,:);

            set(hLeg(k), ...
                'XData', [hip(1), knee(1), foot(1)], ...
                'YData', [hip(2), knee(2), foot(2)], ...
                'ZData', [hip(3), knee(3), foot(3)]);

            set(hFoot(k), ...
                'XData', foot(1), ...
                'YData', foot(2), ...
                'ZData', foot(3));

            i0 = max(1, n - opt.trail_length);

            set(hTrail(k), ...
                'XData', footW.(leg)(i0:n,1), ...
                'YData', footW.(leg)(i0:n,2), ...
                'ZData', footW.(leg)(i0:n,3));
        end

        title(axAnim, sprintf('Quadruped Bezier Trot Animation with IK/FK   t = %.2f s', t(n)));

        drawnow limitrate;
        pause(opt.pause_time);
    end

    % Lưu qLog vào base workspace để kiểm tra nếu cần
    assignin('base', 'qLog_animation', qLog);
end

function opt = set_anim_default_options(opt)
    % Gán giá trị mặc định cho animation nếu user chưa nhập.

    if ~isfield(opt,'frame_skip')
        opt.frame_skip = 2;
    end

    if ~isfield(opt,'pause_time')
        opt.pause_time = 0.01;
    end

    if ~isfield(opt,'trail_length')
        opt.trail_length = 200;
    end

    if ~isfield(opt,'body_length')
        opt.body_length = 0.42;
    end

    if ~isfield(opt,'body_width')
        opt.body_width = 0.20;
    end

    if ~isfield(opt,'body_height')
        opt.body_height = 0.08;
    end

    if ~isfield(opt,'body_z')
        opt.body_z = 0.25;
    end

    if ~isfield(opt,'body_box_offset')
        opt.body_box_offset = 0.03;
    end

    if ~isfield(opt,'use_body_motion')
        opt.use_body_motion = true;
    end

    if ~isfield(opt,'use_yaw_motion')
        opt.use_yaw_motion = true;
    end
    if ~isfield(opt,'L_thigh')
        opt.L_thigh = 0.16;
    end
    
    if ~isfield(opt,'L_shank')
        opt.L_shank = 0.16;
    end
    
    if ~isfield(opt,'knee_direction')
        opt.knee_direction = 1;
    end
end

function p_world = body_to_world(p_body, body_pos, yaw)
    % Đổi tọa độ từ body frame sang world frame.
    %
    % p_body  : [x y z] trong body frame
    % body_pos: [x y z] vị trí gốc body frame trong world frame
    % yaw     : góc quay quanh trục z

    R = rotz_yaw(yaw);

    p_world = (R * p_body(:)).' + body_pos;
end

function R = rotz_yaw(yaw)
    % Ma trận quay quanh trục z

    c = cos(yaw);
    s = sin(yaw);

    R = [ c, -s, 0;
          s,  c, 0;
          0,  0, 1 ];
end

function [V, F] = body_box_vertices(center, yaw, L, W, H)
    % Tạo vertices và faces cho thân robot dạng hình hộp.
    %
    % center: tâm hình hộp trong world frame
    % yaw   : góc quay quanh z
    % L,W,H : dài, rộng, cao

    x = L/2;
    y = W/2;
    z = H/2;

    Vlocal = [ ...
        -x, -y, -z;
         x, -y, -z;
         x,  y, -z;
        -x,  y, -z;
        -x, -y,  z;
         x, -y,  z;
         x,  y,  z;
        -x,  y,  z];

    R = rotz_yaw(yaw);

    V = (R * Vlocal.').';

    V = V + center;

    F = [ ...
        1 2 3 4;   % bottom
        5 6 7 8;   % top
        1 2 6 5;
        2 3 7 6;
        3 4 8 7;
        4 1 5 8 ];
end

function knee = simple_knee_point(hip, foot, body_pos)
    % Tạo điểm knee giả định để animation nhìn giống chân robot.
    %
    % Đây chưa phải FK thật. Sau này khi có IK/FK, sẽ thay hàm này bằng
    % vị trí khớp gối tính từ q_d.

    mid = 0.5 * (hip + foot);

    % Hướng đẩy gối ra ngoài thân
    out = hip(1:2) - body_pos(1:2);

    if norm(out) < 1e-6
        out = [0, 1];
    else
        out = out / norm(out);
    end

    knee = mid;

    % Đẩy gối ra ngoài một chút để chân không thành đường thẳng
    knee(1:2) = knee(1:2) + 0.035 * out;

    % Hạ gối xuống một chút
    knee(3) = mid(3) - 0.045;
end

function q = leg_ik_3dof(p_rel, geom)
    % IK cho chân 3DOF đơn giản:
    %
    % Input:
    % p_rel = [x y z] vị trí bàn chân so với hip, trong body frame
    %
    % Quy ước:
    % x: phía trước robot
    % y: bên trái robot
    % z: hướng lên
    %
    % q1: hip ab/ad, quay quanh trục x
    % q2: hip pitch
    % q3: knee pitch

    L1 = geom.L_thigh;
    L2 = geom.L_shank;

    if isfield(geom,'knee_direction')
        knee_direction = geom.knee_direction;
    else
        knee_direction = 1;
    end

    x = p_rel(1);
    y = p_rel(2);
    z = p_rel(3);

    % ------------------------------------------------------
    % q1: đưa chân về mặt phẳng sagittal x-z
    % ------------------------------------------------------
    q1 = atan2(y, -z);

    R = rotx_local(-q1);
    p_sag = R * p_rel(:);

    xs = p_sag(1);
    zs = p_sag(3);

    % Dùng z_down dương cho bài toán 2-link phẳng
    z_down = -zs;

    % ------------------------------------------------------
    % IK 2-link trong mặt phẳng x-z
    % ------------------------------------------------------
    r2 = xs^2 + z_down^2;

    c3 = (r2 - L1^2 - L2^2) / (2*L1*L2);
    c3 = max(min(c3, 1), -1);

    q3 = knee_direction * acos(c3);

    k1 = L1 + L2*cos(q3);
    k2 = L2*sin(q3);

    q2 = atan2(xs, z_down) - atan2(k2, k1);

    q = [q1, q2, q3];
end

function [hip_rel, knee_rel, foot_rel] = leg_fk_3dof(q, geom)
    % FK cho chân 3DOF tương ứng với leg_ik_3dof.
    %
    % Output:
    % hip_rel, knee_rel, foot_rel là các điểm so với hip.

    L1 = geom.L_thigh;
    L2 = geom.L_shank;

    q1 = q(1);
    q2 = q(2);
    q3 = q(3);

    hip_rel = [0, 0, 0];

    % FK trong mặt phẳng sagittal trước
    knee_sag = [ ...
        L1*sin(q2);
        0;
       -L1*cos(q2)];

    foot_sag = [ ...
        L1*sin(q2) + L2*sin(q2 + q3);
        0;
       -L1*cos(q2) - L2*cos(q2 + q3)];

    % Quay ra không gian 3D bằng q1
    R = rotx_local(q1);

    knee_rel = (R * knee_sag).';
    foot_rel = (R * foot_sag).';
end

function R = rotx_local(a)
    ca = cos(a);
    sa = sin(a);

    R = [1,  0,   0;
         0, ca, -sa;
         0, sa,  ca];
end

function joint_ref = generate_joint_references(t, traj, P3, geom)
    % Tạo qd, qd_dot, qd_ddot cho 4 chân từ quỹ đạo bàn chân.
    %
    % Input:
    % traj.(leg).pos : p_d(t) trong body frame
    %
    % Output:
    % joint_ref.(leg).qd
    % joint_ref.(leg).qd_dot
    % joint_ref.(leg).qd_ddot

    legs = {'FL','FR','RL','RR'};
    dt = t(2) - t(1);

    joint_ref = struct();

    for k = 1:numel(legs)
        leg = legs{k};

        p = traj.(leg).pos;
        N = size(p,1);

        qd = zeros(N,3);

        hip_body = [P3.(leg)(1), P3.(leg)(2), 0];

        for n = 1:N
            foot_body = p(n,:);

            % Vị trí bàn chân so với hip
            p_rel = foot_body - hip_body;

            % IK
            qd(n,:) = leg_ik_3dof(p_rel, geom);
        end

        % Tránh nhảy góc do wrap atan2
        qd = unwrap(qd);

        % Tính đạo hàm số
        qd_dot = zeros(size(qd));
        qd_ddot = zeros(size(qd));

        for j = 1:3
            qd_dot(:,j)  = gradient(qd(:,j), dt);
            qd_ddot(:,j) = gradient(qd_dot(:,j), dt);
        end

        joint_ref.(leg).qd = qd;
        joint_ref.(leg).qd_dot = qd_dot;
        joint_ref.(leg).qd_ddot = qd_ddot;
    end
end

function check_ik_fk_error(t, traj, P3, joint_ref, geom)
    legs = {'FL','FR','RL','RR'};

    fprintf('\n===== IK/FK CHECK =====\n');

    figure('Name','IK/FK Position Error','Color','w');

    for k = 1:numel(legs)
        leg = legs{k};

        p_des = traj.(leg).pos;
        qd = joint_ref.(leg).qd;

        N = size(p_des,1);
        p_fk = zeros(N,3);

        hip_body = [P3.(leg)(1), P3.(leg)(2), 0];

        for n = 1:N
            [~,~,foot_rel] = leg_fk_3dof(qd(n,:), geom);
            p_fk(n,:) = hip_body + foot_rel;
        end

        err = p_des - p_fk;
        err_norm = vecnorm(err,2,2);

        fprintf('%s max IK/FK error = %.6e m\n', leg, max(err_norm));

        subplot(2,2,k);
        plot(t, err_norm, 'LineWidth', 1.5);
        grid on;
        xlabel('time [s]');
        ylabel('error [m]');
        title([leg ' IK/FK position error']);
    end
end

function smc_result = simulate_smc_all_legs(t, joint_ref, smc)
    % Mô phỏng SMC joint tracking cho 4 chân.
    %
    % Mô hình khớp đơn giản:
    % qddot = u
    %
    % Sau này có thể thay bằng:
    % M(q)qddot + C(q,qdot)qdot + G(q) = tau

    legs = {'FL','FR','RL','RR'};
    dt = t(2) - t(1);

    smc_result = struct();

    for k = 1:numel(legs)
        leg = legs{k};

        qd      = joint_ref.(leg).qd;
        qd_dot  = joint_ref.(leg).qd_dot;
        qd_ddot = joint_ref.(leg).qd_ddot;

        N = size(qd,1);
        nJ = size(qd,2);

        q     = zeros(N,nJ);
        q_dot = zeros(N,nJ);
        q_ddot = zeros(N,nJ);
        u     = zeros(N,nJ);
        s_log = zeros(N,nJ);
        e_log = zeros(N,nJ);

        % Điều kiện đầu: cho khớp bắt đầu hơi lệch so với qd để test bám
        q(1,:)     = qd(1,:) + [0.15, -0.10, 0.12];
        q_dot(1,:) = [0, 0, 0];

        for i = 1:N-1

            e     = q(i,:)     - qd(i,:);
            e_dot = q_dot(i,:) - qd_dot(i,:);

            s = e_dot + smc.lambda .* e;

            % Luật SMC:
            % u = qddot_d - lambda*e_dot - k*sat(s/phi)
            u_i = qd_ddot(i,:) ...
                  - smc.lambda .* e_dot ...
                  - smc.k .* sat_vec(s ./ smc.phi);

            % Giới hạn tín hiệu điều khiển
            u_i = max(min(u_i, smc.u_max), -smc.u_max);

            % Mô hình khớp đơn giản qddot = u
            q_ddot(i,:) = u_i;

            % Tích phân Euler
            q_dot(i+1,:) = q_dot(i,:) + q_ddot(i,:) * dt;
            q(i+1,:)     = q(i,:)     + q_dot(i+1,:) * dt;

            u(i,:) = u_i;
            s_log(i,:) = s;
            e_log(i,:) = e;
        end

        % Ghi mẫu cuối
        e_log(end,:) = q(end,:) - qd(end,:);
        s_log(end,:) = q_dot(end,:) - qd_dot(end,:) ...
                       + smc.lambda .* e_log(end,:);

        u(end,:) = u(end-1,:);
        q_ddot(end,:) = q_ddot(end-1,:);

        smc_result.(leg).q = q;
        smc_result.(leg).q_dot = q_dot;
        smc_result.(leg).q_ddot = q_ddot;
        smc_result.(leg).u = u;
        smc_result.(leg).s = s_log;
        smc_result.(leg).e = e_log;

        smc_result.(leg).qd = qd;
        smc_result.(leg).qd_dot = qd_dot;
        smc_result.(leg).qd_ddot = qd_ddot;
    end
end

function y = sat_vec(x)
    % Hàm saturation để giảm chattering
    y = max(min(x, 1), -1);
end

function plot_smc_tracking_result(t, smc_result, leg)
    % Vẽ kết quả tracking q -> qd cho một chân

    q  = smc_result.(leg).q;
    qd = smc_result.(leg).qd;

    q_dot  = smc_result.(leg).q_dot;
    qd_dot = smc_result.(leg).qd_dot;

    e = smc_result.(leg).e;
    s = smc_result.(leg).s;
    u = smc_result.(leg).u;

    figure('Name',[leg ' SMC Joint Tracking'],'Color','w');

    subplot(4,1,1);
    plot(t, qd(:,1),'r--', t, q(:,1),'r', ...
         t, qd(:,2),'g--', t, q(:,2),'g', ...
         t, qd(:,3),'b--', t, q(:,3),'b', ...
         'LineWidth',1.2);
    grid on;
    ylabel('q [rad]');
    title([leg ' joint tracking: desired vs actual']);
    legend('q1d','q1','q2d','q2','q3d','q3');

    subplot(4,1,2);
    plot(t, qd_dot(:,1),'r--', t, q_dot(:,1),'r', ...
         t, qd_dot(:,2),'g--', t, q_dot(:,2),'g', ...
         t, qd_dot(:,3),'b--', t, q_dot(:,3),'b', ...
         'LineWidth',1.2);
    grid on;
    ylabel('qdot [rad/s]');
    title('Joint velocity tracking');
    legend('q1dot_d','q1dot','q2dot_d','q2dot','q3dot_d','q3dot');

    subplot(4,1,3);
    plot(t, e, 'LineWidth',1.2);
    grid on;
    ylabel('error [rad]');
    title('Tracking error e = q - qd');
    legend('e1','e2','e3');

    subplot(4,1,4);
    plot(t, u, 'LineWidth',1.2);
    grid on;
    ylabel('u');
    xlabel('time [s]');
    title('SMC control input');
    legend('u1','u2','u3');
end

function animate_quadruped_smc(t, smc_result, P3, body_cmd, geom, opt)
    % Animation quadruped robot dùng q thực tế sau SMC:
    %
    % q_SMC(t) -> FK -> hip, knee, foot -> animation
    %
    % Đây là animation sau điều khiển, không dùng trực tiếp p_d nữa.

    if nargin < 6
        opt = struct();
    end

    opt = set_anim_default_options(opt);

    legs = {'FL','FR','RL','RR'};
    N = numel(t);

    %% ------------------------------------------------------
    % 1) Tính chuyển động thân trong world frame
    % ------------------------------------------------------
    body_pos = zeros(N,3);
    body_yaw = zeros(N,1);

    for n = 1:N
        if opt.use_body_motion
            body_pos(n,1) = body_cmd.uax * t(n);
            body_pos(n,2) = body_cmd.uay * t(n);
        else
            body_pos(n,1) = 0;
            body_pos(n,2) = 0;
        end

        body_pos(n,3) = opt.body_z;

        if opt.use_yaw_motion
            body_yaw(n) = body_cmd.uaw * t(n);
        else
            body_yaw(n) = 0;
        end
    end

    %% ------------------------------------------------------
    % 2) Dùng q thực tế sau SMC để tính FK
    % ------------------------------------------------------
    hipW  = struct();
    kneeW = struct();
    footW = struct();

    for k = 1:numel(legs)
        leg = legs{k};

        hipW.(leg)  = zeros(N,3);
        kneeW.(leg) = zeros(N,3);
        footW.(leg) = zeros(N,3);
    end

    for n = 1:N
        for k = 1:numel(legs)
            leg = legs{k};

            % Góc khớp thực tế sau SMC
            q_actual = smc_result.(leg).q(n,:);

            % Hip trong body frame
            hip_body = [P3.(leg)(1), P3.(leg)(2), 0];

            % FK từ q_actual
            [hip_rel, knee_rel, foot_rel] = leg_fk_3dof(q_actual, geom);

            hip_body_fk  = hip_body + hip_rel;
            knee_body_fk = hip_body + knee_rel;
            foot_body_fk = hip_body + foot_rel;

            % Đổi sang world frame
            hipW.(leg)(n,:)  = body_to_world(hip_body_fk,  body_pos(n,:), body_yaw(n));
            kneeW.(leg)(n,:) = body_to_world(knee_body_fk, body_pos(n,:), body_yaw(n));
            footW.(leg)(n,:) = body_to_world(foot_body_fk, body_pos(n,:), body_yaw(n));
        end
    end

    %% ------------------------------------------------------
    % 3) Tạo figure animation
    % ------------------------------------------------------
    figAnim = figure('Name','Quadruped Animation Using q from SMC','Color','w');
    axAnim = axes('Parent', figAnim);

    hold(axAnim, 'on');
    grid(axAnim, 'on');
    axis(axAnim, 'equal');

    xlabel(axAnim, 'X [m]');
    ylabel(axAnim, 'Y [m]');
    zlabel(axAnim, 'Z [m]');
    title(axAnim, 'Quadruped Animation Using Actual Joint Angles from SMC');

    view(axAnim, 40, 25);

    allPts = body_pos;

    for k = 1:numel(legs)
        leg = legs{k};
        allPts = [allPts; hipW.(leg); kneeW.(leg); footW.(leg)]; %#ok<AGROW>
    end

    margin = 0.25;

    xlim(axAnim, [min(allPts(:,1))-margin, max(allPts(:,1))+margin]);
    ylim(axAnim, [min(allPts(:,2))-margin, max(allPts(:,2))+margin]);
    zlim(axAnim, [0, max(allPts(:,3)) + 0.25]);

    % Đường đi của thân
    plot3(axAnim, body_pos(:,1), body_pos(:,2), body_pos(:,3), ...
        'k--', 'LineWidth', 1.2);

    % Đường mặt đất
    plot3(axAnim, ...
        [min(allPts(:,1))-margin, max(allPts(:,1))+margin], ...
        [0, 0], ...
        [0, 0], ...
        'k:', 'LineWidth', 1.0);

    %% ------------------------------------------------------
    % 4) Vẽ body
    % ------------------------------------------------------
    body_center = body_pos(1,:) + [0, 0, opt.body_box_offset];

    [Vbody, Fbody] = body_box_vertices( ...
        body_center, body_yaw(1), ...
        opt.body_length, opt.body_width, opt.body_height);

    hBody = patch(axAnim, ...
        'Vertices', Vbody, ...
        'Faces', Fbody, ...
        'FaceColor', [0.35 0.65 1.0], ...
        'FaceAlpha', 0.45, ...
        'EdgeColor', [0.1 0.1 0.1], ...
        'LineWidth', 1.2);

    %% ------------------------------------------------------
    % 5) Tạo handle cho chân
    % ------------------------------------------------------
    colorSet = lines(4);

    hLeg   = gobjects(4,1);
    hFoot  = gobjects(4,1);
    hTrail = gobjects(4,1);

    for k = 1:numel(legs)
        leg = legs{k};

        hTrail(k) = plot3(axAnim, nan, nan, nan, ':', ...
            'Color', colorSet(k,:), ...
            'LineWidth', 1.2);

        hLeg(k) = plot3(axAnim, nan, nan, nan, '-o', ...
            'Color', colorSet(k,:), ...
            'LineWidth', 2.5, ...
            'MarkerSize', 5, ...
            'MarkerFaceColor', colorSet(k,:));

        hFoot(k) = plot3(axAnim, nan, nan, nan, 'o', ...
            'Color', colorSet(k,:), ...
            'MarkerSize', 7, ...
            'MarkerFaceColor', colorSet(k,:));

        text(axAnim, hipW.(leg)(1,1), hipW.(leg)(1,2), hipW.(leg)(1,3), ...
            ['  ' leg], ...
            'FontWeight','bold', ...
            'Color', colorSet(k,:));
    end

    legend(axAnim, [hBody; hLeg], [{'Body'}, legs], 'Location','best');

    %% ------------------------------------------------------
    % 6) Animation loop
    % ------------------------------------------------------
    for n = 1:opt.frame_skip:N

        % Update body
        body_center = body_pos(n,:) + [0, 0, opt.body_box_offset];

        [Vbody, ~] = body_box_vertices( ...
            body_center, body_yaw(n), ...
            opt.body_length, opt.body_width, opt.body_height);

        set(hBody, 'Vertices', Vbody);

        % Update 4 chân
        for k = 1:numel(legs)
            leg = legs{k};

            hip  = hipW.(leg)(n,:);
            knee = kneeW.(leg)(n,:);
            foot = footW.(leg)(n,:);

            set(hLeg(k), ...
                'XData', [hip(1), knee(1), foot(1)], ...
                'YData', [hip(2), knee(2), foot(2)], ...
                'ZData', [hip(3), knee(3), foot(3)]);

            set(hFoot(k), ...
                'XData', foot(1), ...
                'YData', foot(2), ...
                'ZData', foot(3));

            i0 = max(1, n - opt.trail_length);

            set(hTrail(k), ...
                'XData', footW.(leg)(i0:n,1), ...
                'YData', footW.(leg)(i0:n,2), ...
                'ZData', footW.(leg)(i0:n,3));
        end

        title(axAnim, sprintf( ...
            'Quadruped Animation Using q from SMC   t = %.2f s', t(n)));

        drawnow limitrate;
        pause(opt.pause_time);
    end

    % Lưu foot thực tế sau SMC để kiểm tra nếu cần
    assignin('base', 'footW_smc_animation', footW);
end

function check_smc_foot_tracking_error(t, traj, smc_result, P3, geom)
    % So sánh:
    % p_d từ Bezier
    % p_actual từ q_SMC -> FK

    legs = {'FL','FR','RL','RR'};

    fprintf('\n===== SMC FOOT TRACKING ERROR =====\n');

    figure('Name','Foot Position Error After SMC','Color','w');

    for k = 1:numel(legs)
        leg = legs{k};

        p_des = traj.(leg).pos;
        q_act = smc_result.(leg).q;

        N = size(p_des,1);
        p_act = zeros(N,3);

        hip_body = [P3.(leg)(1), P3.(leg)(2), 0];

        for n = 1:N
            [~,~,foot_rel] = leg_fk_3dof(q_act(n,:), geom);
            p_act(n,:) = hip_body + foot_rel;
        end

        err = p_des - p_act;
        err_norm = vecnorm(err,2,2);

        fprintf('%s max foot error after SMC = %.6e m\n', leg, max(err_norm));

        subplot(2,2,k);
        plot(t, err_norm, 'LineWidth', 1.5);
        grid on;
        xlabel('time [s]');
        ylabel('error [m]');
        title([leg ' foot error after SMC']);
    end
end