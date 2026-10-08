# Mô phỏng ESP32 trên Wokwi

Wokwi mô phỏng khối cảnh báo. Camera USB, OpenCV và MediaPipe vẫn chạy trên laptop vì Wokwi không mô phỏng camera máy tính hoặc Python MediaPipe.

## Thành phần

- ESP32 DevKit V1.
- LED xanh: trạng thái bình thường.
- LED vàng: cảnh báo sớm.
- LED đỏ: buồn ngủ hoặc dữ liệu giả mạo.
- Buzzer: cảnh báo âm thanh.

## Cách chạy trên trang Wokwi

1. Tạo dự án ESP32 mới tại https://wokwi.com/projects/new/esp32.
2. Thay nội dung `sketch.ino` và `diagram.json` bằng hai tệp trong thư mục này.
3. Nhấn Start Simulation.
4. Chạy `test-wokwi-bridge.ps1` ở thư mục dự án chính để thử đèn và còi.
5. Python điều khiển các trạng thái `NORMAL`, `WARNING`, `DROWSY` và `TAMPER` qua MQTT.

## Nối trực tiếp với camera laptop

1. Build firmware rồi khởi động lại mô phỏng Wokwi trong VS Code.
2. Chạy `run-integrated-wokwi.ps1` ở thư mục dự án chính.
3. Script tự mở broker MQTT trên laptop; ESP32 kết nối đến `host.wokwi.internal:1883`.
4. Python và ESP32 trao đổi lệnh/ACK bằng MQTT QoS 1.

Khi camera phát hiện `DROWSY`, LED đỏ và buzzer Wokwi sẽ bật. `NORMAL` bật
LED xanh, `WARNING` nháy LED vàng, còn `TAMPER` nháy đỏ/vàng.

## Ý nghĩa khi tích hợp thật

Laptop tính trạng thái từ camera. Chỉ sự kiện đã vượt qua HMAC, timestamp và sequence mới được chuyển thành `NORMAL`, `WARNING` hoặc `DROWSY`. Nếu kiểm tra thất bại, laptop gửi `TAMPER` để ESP32 báo lỗi.
