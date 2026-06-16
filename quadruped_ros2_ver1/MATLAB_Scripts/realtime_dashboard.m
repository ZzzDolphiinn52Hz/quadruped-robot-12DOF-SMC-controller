% realtime_dashboard.m
% Bảng điều khiển viễn trắc (Telemetry) hiển thị quỹ đạo 4 chân thời gian thực qua UDP
% Sử dụng Java Sockets tích hợp sẵn trong MATLAB (Không cần Toolbox)

clc; clear; close all;

import java.net.DatagramSocket
import java.net.DatagramPacket

% Đảm bảo port 5555 không bị chiếm
try
    udp_port = 5557;
    socket = DatagramSocket(udp_port);
    socket.setSoTimeout(20); % Timeout 20ms để vòng lặp không bị kẹt
catch
    error('Cổng %d đang bị chiếm. Hãy khởi động lại MATLAB hoặc đổi port.', udp_port);
end

% --- ĐỊNH NGHĨA THEME (SCI-FI DARK MODE) ---
bg_color   = [0.08, 0.09, 0.13];   % Nền cửa sổ tối
ax_color   = [0.12, 0.14, 0.20];   % Nền đồ thị
grid_color = [0.30, 0.40, 0.50];   % Lưới kẻ mờ
text_color = [0.90, 0.90, 0.95];   % Chữ trắng xám
line_color = [0.00, 1.00, 0.80];   % Cyan Neon (Đường quỹ đạo)
dot_color  = [1.00, 0.20, 0.40];   % Hồng Neon (Điểm hiện tại)

% Khởi tạo giao diện 4 đồ thị
fig = figure('Name', 'Quadruped 12-DOF Real-time Telemetry', 'NumberTitle', 'off', 'Color', bg_color);
fig.Position = [100, 100, 1100, 650];

try
    sgtitle('QUADRUPED KINEMATIC TELEMETRY DASHBOARD', 'Color', 'w', 'FontSize', 18, 'FontWeight', 'bold', 'FontName', 'Trebuchet MS');
catch
    % Fallback cho MATLAB quá cũ không hỗ trợ sgtitle
end

legs = {'FL (Front-Left)', 'FR (Front-Right)', 'RL (Rear-Left)', 'RR (Rear-Right)'};
h_lines = gobjects(4, 1);
h_points = gobjects(4, 1);

max_points = 80; % Số lượng điểm vẽ (Độ dài cái đuôi dài hơn để mượt)
x_data = zeros(max_points, 4);
z_data = zeros(max_points, 4);
point_idx = 1;
is_filled = false;

for i = 1:4
    ax = subplot(2, 2, i);
    
    % Cấu hình trục
    set(ax, 'Color', ax_color, 'XColor', text_color, 'YColor', text_color, ...
            'GridColor', grid_color, 'GridAlpha', 0.5, 'LineWidth', 1.2, ...
            'FontName', 'Consolas', 'FontSize', 10);
    hold on;
    
    % Đường quỹ đạo (Dày, màu Cyan phát sáng)
    h_lines(i) = plot(nan, nan, '-', 'Color', line_color, 'LineWidth', 3.0);
    
    % Dấu chấm (Màu hồng neon, viền trắng nổi bật)
    h_points(i) = plot(nan, nan, 'o', 'MarkerEdgeColor', 'w', 'MarkerFaceColor', dot_color, 'MarkerSize', 8, 'LineWidth', 1.5);
    
    xlabel('X-Axis (m)', 'Color', text_color, 'FontWeight', 'bold');
    ylabel('Z-Axis (m)', 'Color', text_color, 'FontWeight', 'bold');
    title(legs{i}, 'Color', line_color, 'FontWeight', 'bold', 'FontSize', 12);
    
    grid on;
    axis equal;
    
    % Khóa giới hạn trục để đồ thị đứng yên, chỉ có quỹ đạo trôi
    xlim([-0.05, 0.05]); 
    ylim([-0.25, -0.18]); 
end

disp('--- REAL-TIME DASHBOARD ĐÃ SẴN SÀNG ---');
disp('Đang chờ dữ liệu từ Webots (Port 5555)...');
disp('Hãy nhấn Play trong Webots để bắt đầu!');
disp('Đóng cửa sổ đồ thị này để dừng chương trình.');

% Khởi tạo gói tin nhận
buffer = zeros(1, 256, 'int8');
packet = DatagramPacket(buffer, 256);

% Vòng lặp nhận dữ liệu
while ishandle(fig)
    has_data = false;
    latest_msg = "";
    
    try
        % Đọc liên tục cho đến khi rỗng để lấy gói tin mới nhất (chống trễ)
        while true
            socket.receive(packet);
            data = packet.getData();
            len = packet.getLength();
            latest_msg = string(char(data(1:len)'));
            has_data = true;
        end
    catch
        % Nghỉ vòng lặp khi hết gói tin (Socket Timeout)
    end
    
    if has_data
        % Tách chuỗi CSV
        vals = str2double(split(latest_msg, ','));
        
        % Hỗ trợ cả format cũ (9 giá trị) và mới (49 giá trị)
        if length(vals) == 9 || length(vals) == 49
            for i = 1:4
                if length(vals) == 9
                    x = vals(2 + (i-1)*2);
                    z = vals(3 + (i-1)*2);
                else
                    % Format mới: trích q1d (pitch), q2d (knee) → FK ra x,z
                    base = 2 + (i-1)*12;
                    q1d = vals(base + 2);  % q1d (pitch desired)
                    q2d = vals(base + 4);  % q2d (knee desired)
                    L1 = 0.16; L2 = 0.16;
                    x = L1*sin(q1d) + L2*sin(q1d + q2d);
                    z = -(L1*cos(q1d) + L2*cos(q1d + q2d));
                end
                
                % Cuốn dữ liệu (Ring buffer) để tạo hiệu ứng "đuôi sao chổi"
                if is_filled
                    x_data(:, i) = [x_data(2:end, i); x];
                    z_data(:, i) = [z_data(2:end, i); z];
                else
                    x_data(point_idx, i) = x;
                    z_data(point_idx, i) = z;
                end
                
                % Cập nhật lên đồ thị với tốc độ cao
                if is_filled
                    set(h_lines(i), 'XData', x_data(:, i), 'YData', z_data(:, i));
                else
                    set(h_lines(i), 'XData', x_data(1:point_idx, i), 'YData', z_data(1:point_idx, i));
                end
                set(h_points(i), 'XData', x, 'YData', z);
            end
            
            if ~is_filled
                point_idx = point_idx + 1;
                if point_idx > max_points
                    is_filled = true;
                end
            end
            
            drawnow limitrate; % Render đồ thị
        end
    else
        pause(0.01);
    end
end

% Đóng socket an toàn
try socket.close(); catch; end
disp('Đã đóng kết nối UDP.');
