#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MadenBot Lisans Sunucusu
Render.com'a yuklenecek Flask API
"""

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import secrets
import os
import pytz

app = Flask(__name__)

ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "madenbot_admin_2024")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///licenses.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

TURKEY = pytz.timezone("Europe/Istanbul")

def now_tr():
    """Turkiye saatiyle simdiki zaman (timezone-naive, DB icin)"""
    return datetime.now(TURKEY).replace(tzinfo=None)

# --- MODEL ---
class License(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    key         = db.Column(db.String(32), unique=True, nullable=False)
    username    = db.Column(db.String(100), nullable=False)
    plan        = db.Column(db.String(20), default="monthly")
    created_at  = db.Column(db.DateTime, default=now_tr)
    expires_at  = db.Column(db.DateTime, nullable=True)
    active      = db.Column(db.Boolean, default=True)
    last_seen   = db.Column(db.DateTime, nullable=True)
    hwid        = db.Column(db.String(64), nullable=True)

with app.app_context():
    db.create_all()

def admin_required(req):
    return req.headers.get("X-Admin-Secret") == ADMIN_SECRET

def key_status(lic):
    if not lic.active:
        return "inactive"
    if lic.expires_at and now_tr() > lic.expires_at:
        return "expired"
    return "valid"

@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json(silent=True) or {}
    key  = data.get("key", "").strip()
    hwid = data.get("hwid", "")
    if not key:
        return jsonify({"valid": False, "reason": "Key bos"}), 400
    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"valid": False, "reason": "Gecersiz key"}), 200
    status = key_status(lic)
    if status != "valid":
        return jsonify({"valid": False, "reason": status}), 200
    if not lic.hwid:
        lic.hwid = hwid
    elif lic.hwid != hwid:
        return jsonify({"valid": False, "reason": "Farkli bilgisayar"}), 200
    lic.last_seen = now_tr()
    db.session.commit()
    expires_str = lic.expires_at.strftime("%d.%m.%Y %H:%M") if lic.expires_at else "Sinirsiz"
    return jsonify({"valid": True, "username": lic.username, "plan": lic.plan, "expires": expires_str}), 200

@app.route("/admin/list", methods=["GET"])
def admin_list():
    if not admin_required(request):
        return jsonify({"error": "Yetkisiz"}), 403
    licenses = License.query.order_by(License.created_at.desc()).all()
    result = []
    for lic in licenses:
        result.append({
            "id":         lic.id,
            "key":        lic.key,
            "username":   lic.username,
            "plan":       lic.plan,
            "status":     key_status(lic),
            "created_at": lic.created_at.strftime("%d.%m.%Y %H:%M"),
            "expires_at": lic.expires_at.strftime("%d.%m.%Y %H:%M") if lic.expires_at else "Sinirsiz",
            "last_seen":  lic.last_seen.strftime("%d.%m.%Y %H:%M") if lic.last_seen else "Hic",
            "hwid":       lic.hwid or "-",
        })
    return jsonify(result), 200

@app.route("/admin/create", methods=["POST"])
def admin_create():
    if not admin_required(request):
        return jsonify({"error": "Yetkisiz"}), 403
    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    plan     = data.get("plan", "monthly")
    days     = data.get("days", 30)
    if not username:
        return jsonify({"error": "Kullanici adi gerekli"}), 400
    key = secrets.token_hex(8).upper()
    if plan == "lifetime":
        expires_at = None
    else:
        expires_at = now_tr() + timedelta(days=float(days))
    lic = License(key=key, username=username, plan=plan, expires_at=expires_at)
    db.session.add(lic)
    db.session.commit()
    return jsonify({
        "key":      key,
        "username": username,
        "plan":     plan,
        "expires":  expires_at.strftime("%d.%m.%Y %H:%M") if expires_at else "Sinirsiz",
    }), 200

@app.route("/admin/toggle", methods=["POST"])
def admin_toggle():
    if not admin_required(request):
        return jsonify({"error": "Yetkisiz"}), 403
    data = request.get_json(silent=True) or {}
    lic  = License.query.get(data.get("id"))
    if not lic:
        return jsonify({"error": "Bulunamadi"}), 404
    lic.active = not lic.active
    db.session.commit()
    return jsonify({"active": lic.active}), 200

@app.route("/admin/delete", methods=["POST"])
def admin_delete():
    if not admin_required(request):
        return jsonify({"error": "Yetkisiz"}), 403
    data = request.get_json(silent=True) or {}
    lic  = License.query.get(data.get("id"))
    if not lic:
        return jsonify({"error": "Bulunamadi"}), 404
    db.session.delete(lic)
    db.session.commit()
    return jsonify({"ok": True}), 200

@app.route("/admin/extend", methods=["POST"])
def admin_extend():
    if not admin_required(request):
        return jsonify({"error": "Yetkisiz"}), 403
    data = request.get_json(silent=True) or {}
    lic  = License.query.get(data.get("id"))
    days = float(data.get("days", 30))
    if not lic:
        return jsonify({"error": "Bulunamadi"}), 404
    base = max(lic.expires_at or now_tr(), now_tr())
    lic.expires_at = base + timedelta(days=days)
    db.session.commit()
    return jsonify({"expires": lic.expires_at.strftime("%d.%m.%Y %H:%M")}), 200

@app.route("/admin/reset_hwid", methods=["POST"])
def admin_reset_hwid():
    if not admin_required(request):
        return jsonify({"error": "Yetkisiz"}), 403
    data = request.get_json(silent=True) or {}
    lic  = License.query.get(data.get("id"))
    if not lic:
        return jsonify({"error": "Bulunamadi"}), 404
    lic.hwid = None
    db.session.commit()
    return jsonify({"ok": True}), 200

@app.route("/")
def index():
    return jsonify({"status": "MadenBot License Server v1.0"}), 200

if __name__ == "__main__":
    app.run(debug=False)