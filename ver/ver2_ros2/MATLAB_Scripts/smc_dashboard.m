% smc_dashboard.m
% ═══════════════════════════════════════════════════════════════════════════
% REAL-TIME SMC TELEMETRY DASHBOARD CHO ROBOT QUADRUPED 12-DOF
% ═══════════════════════════════════════════════════════════════════════════
% Hiển thị 3 Figure, mỗi Figure có 4 hàng (4 chân xếp dọc):
%   Figure 1: Tín hiệu đặt q_d vs tín hiệu bám q (3 khớp)
%   Figure 2: Sai số mặt trượt s (3 khớp)
%   Figure 3: Momen lực τ (3 khớp)
%
% Nền trắng — Phong cách báo cáo khoa học (Publication-ready)
% ═══════════════════════════════════════════════════════════════════════════

clc; clear; close all;

import java.net.DatagramSocket
import java.net.DatagramPacket

%% ─── CẤU HÌNH ───────────────────────────────────────────────────────────
UDP_PORT    = 5555;
WINDOW_SEC  = 10;
SAMPLE_RATE = 50;
MAX_POINTS  = WINDOW_SEC * SAMPLE_RATE;

%% ─── BẢNG MÀU HỌC THUẬT (NỀN TRẮNG) ──────────────────────────────────
% Màu IEEE/Elsevier-style: tương phản tốt trên nền trắng, in đen trắng vẫn phân biệt được
color_yaw   = [0.85 0.33 0.10];    % Cam đỏ (Vermillion)
color_pitch = [0.00 0.45 0.74];    % Xanh dương đậm (Blue)
color_knee  = [0.47 0.67 0.19];    % Xanh lá (Bluish green)

% q_d: cùng màu nhưng nhạt hơn (alpha effect)
color_yaw_d   = [0.93 0.65 0.50];
color_pitch_d = [0.50 0.73 0.90];
color_knee_d  = [0.72 0.84 0.56];

ax_font  = 'Times New Roman';
ax_fsize = 11;
title_fsize = 12;
label_color = 'k';

%% ─── KẾT NỐI UDP ───────────────────────────────────────────────────────
try
    socket = DatagramSocket(UDP_PORT);
    socket.setSoTimeout(20);
catch ME
    error('Cổng %d đang bị chiếm. Khởi động lại MATLAB hoặc đổi port.', UDP_PORT);
end

%% ─── KHỞI TẠO DỮ LIỆU ─────────────────────────────────────────────────
t_data = zeros(MAX_POINTS, 1);
leg_data = zeros(MAX_POINTS, 12, 4);

legs_short = {'FL', 'FR', 'RL', 'RR'};
legs_full  = {'Front-Left (FL)', 'Front-Right (FR)', 'Rear-Left (RL)', 'Rear-Right (RR)'};

colors_d = {color_yaw_d, color_pitch_d, color_knee_d};
colors_q = {color_yaw, color_pitch, color_knee};

%% ─── HELPER: Cấu hình trục ─────────────────────────────────────────────
setup_ax = @(ax) set(ax, 'Color', 'w', 'XColor', 'k', 'YColor', 'k', ...
    'GridColor', [0.80 0.80 0.80], 'GridAlpha', 0.6, ...
    'FontName', 'Times New Roman', 'FontSize', 11, ...
    'LineWidth', 0.8, 'Box', 'on', 'TickDir', 'out');

%% ═══ FIGURE 1: q_d vs q ════════════════════════════════════════════════
fig1 = figure('Name', 'Joint Tracking - q_d vs q', 'NumberTitle', 'off', 'Color', 'w');
fig1.Position = [30, 150, 1400, 700];
try sgtitle('Joint Position Tracking: q_d (desired) vs q (actual)', ...
        'FontSize', 16, 'FontWeight', 'bold', 'FontName', ax_font, 'Color', 'k'); catch; end

h_qd = gobjects(3, 4);
h_q  = gobjects(3, 4);

for leg = 1:4
    ax = subplot(4, 1, leg, 'Parent', fig1);
    setup_ax(ax); grid(ax, 'on');
    hold on;
    ylabel([legs_short{leg} ' (rad)'], 'FontName', ax_font, 'FontSize', ax_fsize, ...
        'FontWeight', 'bold', 'Color', label_color);
    if leg == 4
        xlabel('Time (s)', 'FontName', ax_font, 'FontSize', ax_fsize, 'Color', label_color);
    else
        set(ax, 'XTickLabel', []);
    end
    title(legs_full{leg}, 'FontName', ax_font, 'FontSize', title_fsize, 'FontWeight', 'bold', 'Color', 'k');
    
    for j = 1:3
        h_qd(j, leg) = plot(nan, nan, '--', 'Color', colors_d{j}, 'LineWidth', 1.5);
        h_q(j, leg)  = plot(nan, nan, '-',  'Color', colors_q{j}, 'LineWidth', 1.8);
    end
    
end

% Legend riêng ở ngoài, trên cùng figure
ax_lgd1 = axes('Parent', fig1, 'Position', [0 0 1 1], 'Visible', 'off');
hold(ax_lgd1, 'on');
p1 = plot(ax_lgd1, nan, nan, '--', 'Color', color_yaw_d, 'LineWidth', 2);
p2 = plot(ax_lgd1, nan, nan, '-',  'Color', color_yaw, 'LineWidth', 2);
p3 = plot(ax_lgd1, nan, nan, '--', 'Color', color_pitch_d, 'LineWidth', 2);
p4 = plot(ax_lgd1, nan, nan, '-',  'Color', color_pitch, 'LineWidth', 2);
p5 = plot(ax_lgd1, nan, nan, '--', 'Color', color_knee_d, 'LineWidth', 2);
p6 = plot(ax_lgd1, nan, nan, '-',  'Color', color_knee, 'LineWidth', 2);
lgd1 = legend([p1 p2 p3 p4 p5 p6], ...
    {'q_{d,yaw}','q_{yaw}', 'q_{d,pitch}','q_{pitch}', 'q_{d,knee}','q_{knee}'}, ...
    'FontSize', 11, 'FontName', ax_font, 'Orientation', 'horizontal', ...
    'Box', 'on', 'EdgeColor', [0.5 0.5 0.5], 'TextColor', 'k', 'Color', 'w');
lgd1.Position = [0.25 0.01 0.50 0.03];

%% ═══ FIGURE 2: Sliding Surface s ═══════════════════════════════════════
fig2 = figure('Name', 'Sliding Surface Error - s', 'NumberTitle', 'off', 'Color', 'w');
fig2.Position = [60, 120, 1400, 700];
try sgtitle('Sliding Surface Error:  s = \Delta(dq) + \lambda\cdot\Deltaq', ...
        'FontSize', 16, 'FontWeight', 'bold', 'FontName', ax_font, 'Color', 'k', ...
        'Interpreter', 'tex'); catch; end

h_s = gobjects(3, 4);

for leg = 1:4
    ax = subplot(4, 1, leg, 'Parent', fig2);
    setup_ax(ax); grid(ax, 'on');
    hold on;
    ylabel([legs_short{leg} ' (rad/s)'], 'FontName', ax_font, 'FontSize', ax_fsize, ...
        'FontWeight', 'bold', 'Color', label_color);
    if leg == 4
        xlabel('Time (s)', 'FontName', ax_font, 'FontSize', ax_fsize, 'Color', label_color);
    else
        set(ax, 'XTickLabel', []);
    end
    title(legs_full{leg}, 'FontName', ax_font, 'FontSize', title_fsize, 'FontWeight', 'bold', 'Color', 'k');
    
    yline(0, '-', 'Color', [0.6 0.6 0.6], 'LineWidth', 0.6);
    
    for j = 1:3
        h_s(j, leg) = plot(nan, nan, '-', 'Color', colors_q{j}, 'LineWidth', 1.5);
    end
    
end

ax_lgd2 = axes('Parent', fig2, 'Position', [0 0 1 1], 'Visible', 'off');
hold(ax_lgd2, 'on');
ps1 = plot(ax_lgd2, nan, nan, '-', 'Color', color_yaw, 'LineWidth', 2);
ps2 = plot(ax_lgd2, nan, nan, '-', 'Color', color_pitch, 'LineWidth', 2);
ps3 = plot(ax_lgd2, nan, nan, '-', 'Color', color_knee, 'LineWidth', 2);
lgd2 = legend([ps1 ps2 ps3], {'s_{yaw}', 's_{pitch}', 's_{knee}'}, ...
    'FontSize', 11, 'FontName', ax_font, 'Orientation', 'horizontal', ...
    'Box', 'on', 'EdgeColor', [0.5 0.5 0.5], 'TextColor', 'k', 'Color', 'w');
lgd2.Position = [0.35 0.01 0.30 0.03];

%% ═══ FIGURE 3: Torque τ ════════════════════════════════════════════════
fig3 = figure('Name', 'Control Torque - τ', 'NumberTitle', 'off', 'Color', 'w');
fig3.Position = [90, 90, 1400, 700];
try sgtitle('SMC Control Torque  \tau  (N\cdotm)', ...
        'FontSize', 16, 'FontWeight', 'bold', 'FontName', ax_font, 'Color', 'k'); catch; end

h_tau = gobjects(3, 4);

for leg = 1:4
    ax = subplot(4, 1, leg, 'Parent', fig3);
    setup_ax(ax); grid(ax, 'on');
    hold on;
    ylabel([legs_short{leg} ' (N\cdotm)'], 'FontName', ax_font, 'FontSize', ax_fsize, ...
        'FontWeight', 'bold', 'Color', label_color);
    if leg == 4
        xlabel('Time (s)', 'FontName', ax_font, 'FontSize', ax_fsize, 'Color', label_color);
    else
        set(ax, 'XTickLabel', []);
    end
    title(legs_full{leg}, 'FontName', ax_font, 'FontSize', title_fsize, 'FontWeight', 'bold', 'Color', 'k');
    
    yline(5, '-.', 'Color', [0.7 0.15 0.15], 'LineWidth', 1.0, 'Label', '+5 N\cdotm', ...
        'FontSize', 9, 'FontName', ax_font, 'LabelHorizontalAlignment', 'left');
    yline(-5, '-.', 'Color', [0.7 0.15 0.15], 'LineWidth', 1.0, 'Label', '-5 N\cdotm', ...
        'FontSize', 9, 'FontName', ax_font, 'LabelHorizontalAlignment', 'left');
    
    for j = 1:3
        h_tau(j, leg) = plot(nan, nan, '-', 'Color', colors_q{j}, 'LineWidth', 1.5);
    end
    
end

ax_lgd3 = axes('Parent', fig3, 'Position', [0 0 1 1], 'Visible', 'off');
hold(ax_lgd3, 'on');
pt1 = plot(ax_lgd3, nan, nan, '-', 'Color', color_yaw, 'LineWidth', 2);
pt2 = plot(ax_lgd3, nan, nan, '-', 'Color', color_pitch, 'LineWidth', 2);
pt3 = plot(ax_lgd3, nan, nan, '-', 'Color', color_knee, 'LineWidth', 2);
lgd3 = legend([pt1 pt2 pt3], {'\tau_{yaw}', '\tau_{pitch}', '\tau_{knee}'}, ...
    'FontSize', 11, 'FontName', ax_font, 'Orientation', 'horizontal', ...
    'Box', 'on', 'EdgeColor', [0.5 0.5 0.5], 'TextColor', 'k', 'Color', 'w');
lgd3.Position = [0.35 0.01 0.30 0.03];

%% ─── THÔNG BÁO ─────────────────────────────────────────────────────────
fprintf('\n  SMC DASHBOARD (Publication Mode) — Đang chờ Webots (Port %d)...\n', UDP_PORT);
fprintf('  Đóng bất kỳ Figure để dừng.\n\n');

%% ─── VÒNG LẶP REALTIME ─────────────────────────────────────────────────
buf = zeros(1, 2048, 'int8');
packet = DatagramPacket(buf, 2048);
sample_count = 0;
t_start = NaN;  % Sẽ lấy timestamp đầu tiên làm gốc

while ishandle(fig1) && ishandle(fig2) && ishandle(fig3)
    has_data = false;
    latest_msg = "";
    
    try
        while true
            socket.receive(packet);
            data = packet.getData();
            len = packet.getLength();
            latest_msg = string(char(data(1:len)'));
            has_data = true;
        end
    catch
    end
    
    if has_data
        vals = str2double(split(latest_msg, ','));
        
        if length(vals) == 49
            sample_count = sample_count + 1;
            
            if sample_count <= MAX_POINTS
                idx = sample_count;
                t_data(idx) = vals(1);
                if isnan(t_start), t_start = vals(1); end
                for leg = 1:4
                    base = 2 + (leg-1) * 12;
                    leg_data(idx, :, leg) = vals(base:base+11)';
                end
            else
                t_data = [t_data(2:end); vals(1)];
                for leg = 1:4
                    base = 2 + (leg-1) * 12;
                    leg_data(:, :, leg) = [leg_data(2:end, :, leg); vals(base:base+11)'];
                end
            end
            
            n = min(sample_count, MAX_POINTS);
            t_plot = t_data(1:n) - t_start;  % Thời gian tương đối (bắt đầu từ 0)
            
            for leg = 1:4
                d = leg_data(1:n, :, leg);
                
                set(h_qd(1, leg), 'XData', t_plot, 'YData', d(:,1));
                set(h_q(1, leg),  'XData', t_plot, 'YData', d(:,2));
                set(h_qd(2, leg), 'XData', t_plot, 'YData', d(:,3));
                set(h_q(2, leg),  'XData', t_plot, 'YData', d(:,4));
                set(h_qd(3, leg), 'XData', t_plot, 'YData', d(:,5));
                set(h_q(3, leg),  'XData', t_plot, 'YData', d(:,6));
                
                set(h_s(1, leg), 'XData', t_plot, 'YData', d(:,7));
                set(h_s(2, leg), 'XData', t_plot, 'YData', d(:,8));
                set(h_s(3, leg), 'XData', t_plot, 'YData', d(:,9));
                
                set(h_tau(1, leg), 'XData', t_plot, 'YData', d(:,10));
                set(h_tau(2, leg), 'XData', t_plot, 'YData', d(:,11));
                set(h_tau(3, leg), 'XData', t_plot, 'YData', d(:,12));
            end
            
            if n > 1
                t_min = t_plot(1);
                t_max = t_plot(end);
                for leg = 1:4
                    subplot(4,1,leg,'Parent',fig1); xlim([t_min t_max]);
                    subplot(4,1,leg,'Parent',fig2); xlim([t_min t_max]);
                    subplot(4,1,leg,'Parent',fig3); xlim([t_min t_max]);
                end
            end
            
            drawnow limitrate;
        end
    else
        pause(0.01);
    end
end

try socket.close(); catch; end
fprintf('  Dashboard đã dừng.\n');

