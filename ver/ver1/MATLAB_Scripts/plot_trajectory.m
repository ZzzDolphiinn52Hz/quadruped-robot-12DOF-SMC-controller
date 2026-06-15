% Đọc file CSV bằng đường dẫn tương đối (hoặc tuyệt đối)
data = readmatrix('Dog 12DOF/controllers/SMC_12DOF/trajectory_log.csv'); 

% Vẽ trục x (cột 2) và trục z (cột 3)
plot(data(:, 2), data(:, 3), 'b-', 'LineWidth', 2);
xlabel('Vị trí X (m)'); ylabel('Vị trí Z (m)');
title('Quỹ đạo chân robot thực tế từ Webots (Bézier 6th Order)');
grid on; axis equal;
