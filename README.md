# Hệ thống giám sát buồn ngủ và phát hiện giả mạo dữ liệu

Bản thử nghiệm sử dụng **laptop và camera USB**. Python, OpenCV và MediaPipe xác định độ mở mắt, độ mở miệng và tỷ lệ PERCLOS. Sự kiện được ký bằng HMAC-SHA256; bộ nhận kiểm tra chữ ký, thời gian và số thứ tự để phát hiện sửa dữ liệu hoặc phát lại gói tin.

## Kiến trúc

```text
Camera USB
    |
    v
Laptop: OpenCV + MediaPipe
    |-- EAR: mắt mở/nhắm
    |-- MAR: ngáp
    |-- PERCLOS: tỷ lệ thời gian mắt nhắm
    `-- HMAC + timestamp + sequence
              |
              |-- SQLite + trang giám sát
              `-- MQTT -> ESP32 Wokwi -> LED + buzzer
```

Khối ESP32, LED và buzzer được mô phỏng trong thư mục `wokwi`. Broker MQTT chạy cục bộ trên laptop; không cần Internet sau khi đã cài thư viện.

## Yêu cầu

- Windows 10/11.
- Laptop có Python 3.12 hoặc công cụ `uv`.
- Camera USB. Webcam tích hợp cũng dùng được.

Python 3.13 chưa được chọn vì gói MediaPipe có thể chưa cung cấp wheel tương thích ổn định.

## Cài đặt

Mở PowerShell trong thư mục dự án:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

## Kiểm tra không cần camera

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m driver_monitor simulate
```

Chế độ mô phỏng tạo các trạng thái bình thường, cảnh báo và buồn ngủ, sau đó cố tình sửa và phát lại gói tin để chứng minh bộ kiểm tra từ chối dữ liệu giả.

## Chạy camera USB

Kết nối webcam và chạy:

```powershell
.\run-camera.ps1
```

Script tự dừng phiên camera cũ của chính dự án trước khi mở phiên mới, tránh lỗi
`CameraReservedByAnotherApp`. Hãy đóng ứng dụng Windows Camera, Zoom, Teams hoặc
trình duyệt đang sử dụng webcam trước khi chạy.

Trong 4 giây đầu, giữ mắt mở và nhìn vào camera để hiệu chỉnh EAR. Sau đó:

- Viền mắt xanh khi mở, đỏ khi nhắm; viền miệng chuyển cam khi há/ngáp.

- Nhắm mắt ngắn: không báo động.
- Nhắm mắt khoảng 0,7 giây: cảnh báo.
- Nhắm mắt từ khoảng 1,5 giây: báo động.
- Khi mở mắt lại: còi dừng ngay; PERCLOS cao chỉ tiếp tục nháy cảnh báo vàng.
- Không thấy khuôn mặt trên 2 giây: báo động.
- Nhấn `q` để thoát.

Nếu máy có nhiều camera, đổi `--index 0` thành `--index 1` trong `run-camera.ps1`.
Backend mặc định trên Windows là `msmf`. Nếu một camera cũ không hỗ trợ, có thể
thử `--camera-backend dshow` hoặc `--camera-backend auto`.

## Chạy đồng bộ với Wokwi

Khởi động lại Wokwi Simulator để nạp firmware mới, rồi chạy:

```powershell
.\run-integrated-wokwi.ps1
```

Script tự khởi động broker MQTT nền ở cổng `1883`. Python gửi trạng thái đến topic
`driver/LAPTOP-CAM-01/command`; ESP32 gửi ACK về topic
`driver/LAPTOP-CAM-01/ack`. Khi terminal in `ESP32 MQTT -> ... ACK STATE=DROWSY`,
LED đỏ và buzzer Wokwi đã nhận cùng trạng thái. Loa laptop không được sử dụng.

Để thử riêng ESP32 mà không mở camera:

```powershell
.\test-wokwi-bridge.ps1
```

## Xem dữ liệu

Mở một PowerShell khác:

```powershell
.\run-dashboard.ps1
```

Truy cập `http://127.0.0.1:5000`. Dữ liệu nằm tại `data/events.db`.
SQLite vẫn lưu Unix timestamp để xác thực; dashboard và API bổ sung trường
`timestamp_display` theo định dạng giờ Việt Nam `dd/mm/yyyy HH:MM:SS`.

## Phát hiện giả mạo

Mỗi sự kiện có dạng:

```json
{
  "device_id": "LAPTOP-CAM-01",
  "timestamp": 1760000000,
  "sequence": 12,
  "status": "DROWSY",
  "ear": 0.14,
  "mar": 0.31,
  "perclos": 0.38,
  "signature": "HMAC-SHA256..."
}
```

Bộ nhận từ chối khi:

- Chữ ký sai: giá trị đã bị chỉnh sửa hoặc khóa không đúng.
- Số thứ tự trùng/giảm: gói tin cũ bị phát lại.
- Timestamp quá cũ: dữ liệu không còn hợp lệ.
- Device ID lạ: thiết bị không được đăng ký.

Khóa trong mã chỉ dành cho demo. Khi triển khai, đặt khóa trong biến môi trường hoặc kho bí mật, không commit lên Git.

## Giới hạn

Đây là nguyên mẫu đồ án, không phải thiết bị an toàn ô tô hoặc thiết bị y tế được chứng nhận. Kính râm, ánh sáng kém, camera rung và góc mặt quá lệch có thể làm giảm độ chính xác.
