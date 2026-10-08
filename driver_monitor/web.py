from __future__ import annotations

from pathlib import Path

from .storage import EventStore


def create_app(database: str | Path):
    from flask import Flask, jsonify, render_template_string

    app = Flask(__name__)
    store = EventStore(database)

    template = """
    <!doctype html><html lang="vi"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Giám sát tài xế</title>
    <style>
      body{font-family:system-ui;margin:32px;background:#f4f6f8;color:#17202a}
      main{max-width:1000px;margin:auto;background:white;padding:24px;border-radius:12px}
      table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #ddd;text-align:left}
      .ok{color:#087f23}.bad{color:#b00020}h1{margin-top:0}
    </style></head><body><main><h1>Hệ thống giám sát trạng thái tài xế</h1>
    <p>Tự động làm mới sau 5 giây. Bản ghi không hợp lệ là dữ liệu bị sửa, phát lại hoặc không đúng thiết bị.</p>
    <table><thead><tr><th>Thời gian</th><th>Thiết bị</th><th>Trạng thái</th><th>Kiểm tra</th><th>Lý do</th></tr></thead>
    <tbody>{% for e in events %}<tr><td>{{e.timestamp}}</td><td>{{e.device_id}}</td><td>{{e.status}}</td>
    <td class="{{'ok' if e.accepted else 'bad'}}">{{'Hợp lệ' if e.accepted else 'Giả mạo'}}</td>
    <td>{{e.verification_reason}}</td></tr>{% endfor %}</tbody></table></main>
    <script>setTimeout(()=>location.reload(),5000)</script></body></html>
    """

    @app.get("/")
    def index():
        return render_template_string(template, events=store.latest(100))

    @app.get("/api/events")
    def events():
        return jsonify(store.latest(100))

    return app

