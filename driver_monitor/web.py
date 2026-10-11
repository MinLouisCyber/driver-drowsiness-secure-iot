from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .runtime import MonitorRuntime
from .storage import EventStore

VIETNAM_TIMEZONE = timezone(timedelta(hours=7))


def format_timestamp(value: int | float | str) -> str:
    """Convert a Unix timestamp to a readable Vietnam date and time."""
    try:
        moment = datetime.fromtimestamp(float(value), tz=VIETNAM_TIMEZONE)
    except (TypeError, ValueError, OSError):
        return "Không xác định"
    return moment.strftime("%d/%m/%Y %H:%M:%S")


def present_events(events: list[dict]) -> list[dict]:
    presented = []
    for event in events:
        reason = str(event.get("verification_reason", ""))
        if event.get("accepted"):
            try:
                reasons = json.loads(event.get("payload", "{}")).get("reasons", [])
            except (TypeError, ValueError, json.JSONDecodeError):
                reasons = []
            reason = ", ".join(reasons) if reasons else {
                "NORMAL": "Các chỉ số trong ngưỡng an toàn",
                "WARNING": "Phát hiện dấu hiệu buồn ngủ",
                "DROWSY": "Mắt nhắm kéo dài hoặc mất khuôn mặt",
            }.get(str(event.get("status")), "Dữ liệu hợp lệ")
        else:
            lowered = reason.lower()
            if "signature" in lowered:
                reason = "Chữ ký HMAC không hợp lệ"
            elif "replay" in lowered or "out-of-order" in lowered:
                reason = "Gói tin bị phát lại"
            elif "unknown device" in lowered:
                reason = "Thiết bị không được đăng ký"
            elif "stale" in lowered:
                reason = "Dữ liệu quá cũ"
        presented.append(
            {
                **event,
                "timestamp_display": format_timestamp(event.get("timestamp", 0)),
                "display_reason": reason,
            }
        )
    return presented


TEMPLATE = r"""
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Giám sát an toàn tài xế</title>
  <style>
    :root{color-scheme:dark;--bg:#061426;--panel:#0c2139;--line:#1b3b5d;--text:#eaf4ff;--muted:#8fa9c2;--cyan:#2cbcf3;--green:#35df83;--yellow:#ffbd3e;--red:#ff5267}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font:14px system-ui,Segoe UI,sans-serif}.app{min-height:100vh;display:grid;grid-template-columns:208px 1fr}
    aside{position:sticky;top:0;height:100vh;background:linear-gradient(180deg,#0b2340,#07182c);border-right:1px solid var(--line);padding-top:78px}.brand{position:absolute;top:24px;left:25px;font-weight:900;letter-spacing:.14em;color:#dcecff}.nav{display:grid;gap:10px;padding:10px 6px}.nav a{display:flex;align-items:center;gap:17px;padding:15px 20px;border-radius:7px;color:#c5d8eb;text-decoration:none;font-size:16px}.nav a:hover,.nav a.active{background:linear-gradient(90deg,#195799,#12365e);color:white;box-shadow:inset 3px 0 #3ba4ff}.nav-icon{width:27px;text-align:center;font-size:21px}.content{min-width:0}
    header{min-height:78px;display:flex;align-items:center;justify-content:space-between;padding:14px 28px;border-bottom:1px solid #102944;background:#07172a}
    h1{font-size:32px;margin:0;letter-spacing:.01em}.connections{display:flex;gap:12px;flex-wrap:wrap}.chip{min-width:196px;text-align:center;padding:10px 13px;border:1px solid var(--line);border-radius:9px;background:#091c30;color:var(--muted);font-weight:650}
    .chip.online{border-color:#158c56;color:#b9f8d5}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:currentColor;margin-right:7px}
    main{max-width:1540px;margin:auto;padding:0 18px 18px;display:grid;gap:14px}.panel{background:linear-gradient(145deg,#0d223a,#091a2e);border:1px solid var(--line);border-radius:12px;padding:14px;box-shadow:0 7px 20px #020b1666}
    .top{display:grid;grid-template-columns:minmax(680px,2.2fr) repeat(3,minmax(160px,.55fr));gap:14px}.camera-grid{display:grid;grid-template-columns:minmax(440px,1fr) 190px;gap:15px}
    .camera{background:#020914;border-radius:9px;overflow:hidden;aspect-ratio:16/10;display:grid;place-items:center}.camera img{width:100%;height:100%;object-fit:cover}.camera-note{color:var(--muted)}
    h2{font-size:15px;margin:0 0 12px;color:#cfe6fa}.state{font-size:24px;font-weight:800;text-align:center;padding:14px 8px;border-radius:9px;background:#12354d;color:var(--cyan)}
    .state.NORMAL{background:#0d5535;color:#b9ffda}.state.WARNING{background:#634813;color:#ffe092}.state.DROWSY,.state.TAMPER{background:#651c29;color:#ffb4be}
    .details{display:grid;gap:13px;margin-top:16px;color:var(--muted)}.details span{padding-bottom:8px;border-bottom:1px solid #173652}.details b{display:block;color:var(--text);margin-top:3px;font-size:14px}.metric{text-align:center;display:grid;align-content:start;min-height:278px;padding-top:25px}
    .metric-icon{margin:auto;width:66px;height:66px;border-radius:50%;display:grid;place-items:center;background:#112d4c;color:#d7eaff;font-size:31px}.metric .label{font-weight:800;font-size:20px;color:#cfe6fa;margin-top:11px}.metric strong{font-size:43px;margin:9px 0 3px;color:var(--cyan)}.metric.mar strong{color:var(--yellow)}.metric.perclos strong{color:var(--red)}.spark{height:70px!important;margin-top:3px}
    .middle{display:grid;grid-template-columns:2.4fr 1fr;gap:14px}canvas{width:100%;height:230px;display:block}.chart-head{display:flex;justify-content:space-between;gap:20px}.legend{display:flex;gap:18px;color:var(--muted);font-size:12px}.legend i{display:inline-block;width:18px;height:3px;margin:0 6px 3px 0}.risk{display:grid;align-content:start;gap:13px}
    .risk-head{display:flex;align-items:center;justify-content:space-between;padding:8px 0 5px}.signal{display:flex;align-items:end;gap:4px;height:42px}.signal i{display:block;width:7px;background:var(--green);border-radius:4px}.signal i:nth-child(1){height:14px}.signal i:nth-child(2){height:22px}.signal i:nth-child(3){height:31px}.signal i:nth-child(4){height:40px}.risk-badge{min-width:130px;text-align:center;padding:12px;border:1px solid #28dc77;border-radius:9px;background:#115b37;color:#d8ffea;font-size:22px;font-weight:800}.risk-row{padding:14px 0;border-bottom:1px solid var(--line);color:var(--muted)}.risk-row b{float:right;color:var(--text)}table{width:100%;border-collapse:collapse}
    th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left}th{color:var(--muted);font-weight:600}.valid{color:var(--green)}.invalid{color:var(--red)}.event-state{font-weight:800}.event-state::before{content:'';display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:9px;background:currentColor}.event-state.NORMAL{color:var(--green)}.event-state.WARNING{color:var(--yellow)}.event-state.DROWSY,.event-state.TAMPER{color:var(--red)}.empty{text-align:center;color:var(--muted);padding:30px}.footer-note{color:var(--muted);font-size:12px;margin-top:10px}
    @media(max-width:1200px){.app{grid-template-columns:78px 1fr}.brand{display:none}aside{padding-top:24px}.nav a{padding:14px 18px}.nav a span:last-child{display:none}.top{grid-template-columns:1fr 1fr}.camera-panel{grid-column:1/-1}.middle{grid-template-columns:1fr}.chip{min-width:auto}}
    @media(max-width:700px){.app{display:block}aside{display:none}header{align-items:flex-start;gap:12px;flex-direction:column}h1{font-size:24px}.top{grid-template-columns:1fr}.camera-grid{grid-template-columns:1fr}.connections{display:none}.table-wrap{overflow:auto}}
  </style>
</head>
<body><div class="app">
  <aside><div class="brand">DRIVER IoT</div><nav class="nav">
    <a class="active" href="#overview"><span class="nav-icon">⌂</span><span>Tổng quan</span></a>
    <a href="#charts"><span class="nav-icon">⌁</span><span>Biểu đồ</span></a>
    <a href="#event-section"><span class="nav-icon">▤</span><span>Sự kiện</span></a>
    <a href="#device"><span class="nav-icon">⚙</span><span>Thiết bị</span></a>
    <a href="#event-section"><span class="nav-icon">♢</span><span>Bảo mật</span></a>
  </nav></aside><div class="content">
  <header id="device"><h1>GIÁM SÁT AN TOÀN TÀI XẾ</h1><div class="connections">
    <span id="camera-chip" class="chip"><i class="dot"></i><span>Camera: Đang khởi động</span></span>
    <span id="esp-chip" class="chip"><i class="dot"></i><span>ESP32: Chờ phản hồi</span></span>
    <span id="mqtt-chip" class="chip"><i class="dot"></i><span>MQTT: Chưa kết nối</span></span>
  </div></header>
  <main id="overview">
    <section class="top">
      <article class="panel camera-panel"><h2>Hình ảnh camera (thời gian thực)</h2><div class="camera-grid">
        <div class="camera">{% if live_camera %}<img src="/video-feed" alt="Camera tài xế">{% else %}<span class="camera-note">Chạy chế độ monitor để xem camera</span>{% endif %}</div>
        <div><small>Trạng thái hiện tại</small><div id="level" class="state">CHƯA KHỞI ĐỘNG</div><div class="details">
          <span>Thiết bị <b>LAPTOP-CAM-01</b></span><span>Nhận diện khuôn mặt <b id="face">Không</b></span><span>Thời gian <b id="updated">--:--:--</b></span>
        </div></div></div></article>
      <article class="panel metric"><span class="metric-icon">◉</span><span class="label">EAR</span><strong id="ear">--</strong><canvas class="spark" id="ear-spark"></canvas></article>
      <article class="panel metric mar"><span class="metric-icon">⌒</span><span class="label">MAR</span><strong id="mar">--</strong><canvas class="spark" id="mar-spark"></canvas></article>
      <article class="panel metric perclos"><span class="metric-icon">⌣</span><span class="label">PERCLOS</span><strong id="perclos">0%</strong><canvas class="spark" id="perclos-spark"></canvas></article>
    </section>
    <section class="middle" id="charts">
      <article class="panel"><div class="chart-head"><h2>Biểu đồ chỉ số theo thời gian thực</h2><div class="legend"><span><i style="background:var(--cyan)"></i>EAR</span><span><i style="background:var(--yellow)"></i>MAR</span><span><i style="background:var(--red)"></i>PERCLOS</span></div></div><canvas id="chart"></canvas></article>
      <article class="panel risk"><h2>Đánh giá nguy cơ buồn ngủ</h2><div class="risk-head"><div class="signal"><i></i><i></i><i></i><i></i></div><div id="risk" class="risk-badge">--</div></div><div class="risk-row">Số lần ngáp <b id="yawns">0</b></div><div class="risk-row">Mắt nhắm liên tục <b id="closed">0.0 giây</b></div><div class="risk-row">Nguyên nhân <b id="reason">--</b></div></article>
    </section>
    <section class="panel" id="event-section"><h2>Lịch sử sự kiện</h2><div class="table-wrap"><table><thead><tr><th>Thời gian</th><th>Thiết bị</th><th>Trạng thái</th><th>Xác thực</th><th>Nguyên nhân</th></tr></thead><tbody id="events"><tr><td colspan="5" class="empty">Chưa có sự kiện</td></tr></tbody></table></div></section>
  </main>
  <script>
    const series={ear:[],mar:[],perclos:[]},maxPoints=90,$=id=>document.getElementById(id),fmt=(v,n=3)=>v==null?'--':Number(v).toFixed(n);
    function chip(id,online,onText,offText){const e=$(id);e.classList.toggle('online',online);e.querySelector('span').textContent=online?onText:offText}
    function updateStatus(s){const level=s.level||'OFFLINE',levelText={NORMAL:'BÌNH THƯỜNG',WARNING:'CẢNH BÁO',DROWSY:'BUỒN NGỦ',TAMPER:'GIẢ MẠO',CALIBRATING:'ĐANG HIỆU CHỈNH',OFFLINE:'NGOẠI TUYẾN'}[level]||level,el=$('level');el.textContent=levelText;el.className='state '+level;
      $('ear').textContent=fmt(s.ear);$('mar').textContent=fmt(s.mar);$('perclos').textContent=Math.round((s.perclos||0)*100)+'%';$('face').textContent=s.face_detected?'Có':'Không';$('closed').textContent=fmt(s.eye_closed_for,1)+' giây';$('yawns').textContent=s.yawns||0;
      $('updated').textContent=s.updated_at?new Date(s.updated_at*1000).toLocaleString('vi-VN'):'--';$('reason').textContent=(s.reasons||[]).join(', ')||s.message||'--';const risk=level==='DROWSY'?'Cao':level==='WARNING'?'Trung bình':level==='NORMAL'?'Thấp':'Đang hiệu chỉnh';$('risk').textContent=risk;
      chip('camera-chip',s.camera==='ACTIVE','Camera: Đang hoạt động','Camera: Không hoạt động');chip('mqtt-chip',s.mqtt==='CONNECTED','MQTT: Đã kết nối','MQTT: Chưa kết nối');chip('esp-chip',s.esp32==='ONLINE','ESP32: Trực tuyến','ESP32: Chờ phản hồi');
      [['ear',s.ear],['mar',s.mar],['perclos',s.perclos]].forEach(([k,v])=>{series[k].push(v||0);if(series[k].length>maxPoints)series[k].shift()});drawChart();drawSpark('ear-spark',series.ear,'#2cbcf3');drawSpark('mar-spark',series.mar,'#ffbd3e');drawSpark('perclos-spark',series.perclos,'#ff5267')}
    function drawChart(){const c=$('chart'),d=devicePixelRatio||1,w=c.clientWidth,h=c.clientHeight;c.width=w*d;c.height=h*d;const x=c.getContext('2d');x.scale(d,d);x.clearRect(0,0,w,h);x.strokeStyle='#1b3b5d';x.lineWidth=1;for(let i=0;i<5;i++){let y=15+i*(h-30)/4;x.beginPath();x.moveTo(35,y);x.lineTo(w-10,y);x.stroke()}x.fillStyle='#8fa9c2';x.font='11px system-ui';x.fillText('0.6',5,18);x.fillText('0.3',5,h/2);x.fillText('0.0',5,h-12);[['ear','#2cbcf3'],['mar','#ffbd3e'],['perclos','#ff5267']].forEach(([k,color])=>{x.strokeStyle=color;x.lineWidth=2;x.beginPath();series[k].forEach((v,i)=>{let px=35+i*(w-50)/(maxPoints-1),py=h-15-Math.min(.6,v)*(h-30)/.6;i?x.lineTo(px,py):x.moveTo(px,py)});x.stroke()})}
    function drawSpark(id,data,color){const c=$(id),d=devicePixelRatio||1,w=c.clientWidth,h=c.clientHeight;c.width=w*d;c.height=h*d;const x=c.getContext('2d');x.scale(d,d);x.strokeStyle='#27435f';x.beginPath();x.moveTo(0,h-1);x.lineTo(w,h-1);x.stroke();x.strokeStyle=color;x.lineWidth=2;x.beginPath();data.forEach((v,i)=>{const px=i*w/Math.max(1,maxPoints-1),py=h-5-Math.min(.6,v)*(h-10)/.6;i?x.lineTo(px,py):x.moveTo(px,py)});x.stroke()}
    async function refresh(){try{const [sr,er]=await Promise.all([fetch('/api/status'),fetch('/api/events')]);updateStatus(await sr.json());renderEvents(await er.json())}catch(e){chip('camera-chip',false,'','Camera: Mất kết nối')}}
    function renderEvents(items){const body=$('events');body.innerHTML=items.length?'':'<tr><td colspan="5" class="empty">Chưa có sự kiện</td></tr>';items.slice(0,12).forEach(e=>{const tr=document.createElement('tr');[e.timestamp_display,e.device_id,e.status,e.accepted?'Hợp lệ':'Giả mạo',e.display_reason].forEach((v,i)=>{const td=document.createElement('td');td.textContent=v;if(i===2)td.className='event-state '+e.status;if(i===3)td.className=e.accepted?'valid':'invalid';tr.appendChild(td)});body.appendChild(tr)})}
    refresh();setInterval(refresh,1000);addEventListener('resize',drawChart);
  </script>
  </div></div>
</body></html>
"""


def create_app(database: str | Path, runtime: MonitorRuntime | None = None):
    from flask import Flask, Response, jsonify, render_template_string

    app = Flask(__name__)
    store = EventStore(database)

    @app.get("/")
    def index():
        return render_template_string(TEMPLATE, live_camera=runtime is not None)

    @app.get("/api/events")
    def events():
        return jsonify(present_events(store.latest(100)))

    @app.get("/api/status")
    def status():
        if runtime is None:
            return jsonify({"camera": "OFFLINE", "mqtt": "DISCONNECTED", "level": "OFFLINE", "message": "Camera chưa chạy trong tiến trình dashboard"})
        return jsonify(runtime.status())

    @app.get("/video-feed")
    def video_feed():
        if runtime is None:
            return Response(status=404)

        def frames():
            version = -1
            while True:
                version, jpeg = runtime.wait_for_frame(version)
                if jpeg is not None:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"

        return Response(frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return app
