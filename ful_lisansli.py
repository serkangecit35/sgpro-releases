#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SGPRO GUI Application
Grafik arayüzlü metin taşı avcısı - V12.0 Kızıl Orman
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import sys
import json
import os
import hashlib
import uuid
import logging

# ─────────────────────────────────────────────
#  ANTI-EXTRACT KORUMA
# ─────────────────────────────────────────────
def _integrity_check():
    frozen = getattr(sys, "frozen", False)
    if not frozen:
        sys.exit(0)
    try:
        exe_path = sys.executable
        h = hashlib.sha256()
        with open(exe_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        stored  = os.environ.get("_MH_HASH", "")
        current = h.hexdigest()
        if not stored:
            os.environ["_MH_HASH"] = current
        elif stored != current:
            sys.exit(0)
    except:
        pass

_integrity_check()

# ─────────────────────────────────────────────
#  OTOMATİK GÜNCELLEME
# ─────────────────────────────────────────────
CURRENT_VERSION = "1.0"   # her build'de artır: 1.0 → 1.1 → 1.2

def check_for_update():
    try:
        import urllib.request, tempfile, subprocess
        req = urllib.request.urlopen(
            "https://madenbot-server.onrender.com/version", timeout=5)
        data = json.loads(req.read())
        latest = data.get("version", CURRENT_VERSION)
        url    = data.get("url", "")
        if latest != CURRENT_VERSION and url:
            tmp = os.path.join(tempfile.gettempdir(), "SGPRO_update.exe")
            urllib.request.urlretrieve(url, tmp)
            subprocess.Popen([tmp])
            sys.exit(0)
    except Exception:
        pass  # sunucuya ulaşamazsa sessizce devam et

check_for_update()

# ─────────────────────────────────────────────
#  LİSANS AYARLARI
# ─────────────────────────────────────────────
LICENSE_SERVER = "https://madenbot-server.onrender.com"
KEY_FILE       = os.path.join(os.environ.get("APPDATA", "."), "SGPRO", "license.key")

def get_hwid():
    raw = str(uuid.getnode()) + os.environ.get("COMPUTERNAME", "PC")
    return hashlib.sha256(raw.encode()).hexdigest()[:32]

def load_saved_key():
    try:
        with open(KEY_FILE, "r") as f:
            return f.read().strip()
    except:
        return ""

def save_key(key):
    try:
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
        with open(KEY_FILE, "w") as f:
            f.write(key)
    except:
        pass

def verify_license(key):
    try:
        import urllib.request
        payload = json.dumps({"key": key, "hwid": get_hwid()}).encode()
        req = urllib.request.Request(
            LICENSE_SERVER + "/verify",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("valid"):
                return True, data.get("username", ""), data.get("expires", ""), ""
            else:
                return False, "", "", data.get("reason", "Gecersiz key")
    except Exception as e:
        return False, "", "", "Sunucuya baglanamadi"

# ─────────────────────────────────────────────
#  LİSANS EKRANI
# ─────────────────────────────────────────────
class LicenseScreen:
    BG     = "#0d0f14"
    PANEL  = "#161b22"
    BORDER = "#30363d"
    GREEN  = "#39d353"
    RED    = "#f85149"
    FG     = "#c9d1d9"
    FG_DIM = "#6e7681"

    def __init__(self, root, on_success):
        self.root       = root
        self.on_success = on_success
        self._verifying = False
        self._build()

    def _build(self):
        self.root.title("SGPRO -- Lisans Dogrulama")
        self.root.geometry("420x320")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)

        tk.Label(self.root, text="SGPRO",
                 font=("Consolas", 22, "bold"),
                 bg=self.BG, fg=self.GREEN).pack(pady=(28, 0))
        tk.Label(self.root, text="SGPRO  v12.0  Kizil Orman",
                 font=("Consolas", 9, "bold"),
                 bg=self.BG, fg=self.GREEN).pack()
        tk.Label(self.root, text="Lisans anahtarinizi girin",
                 font=("Consolas", 9), bg=self.BG, fg=self.FG_DIM).pack(pady=(2, 16))

        tk.Frame(self.root, bg=self.BORDER, height=1).pack(fill=tk.X, padx=30)

        key_frame = tk.Frame(self.root, bg=self.BG)
        key_frame.pack(fill=tk.X, padx=30, pady=16)
        tk.Label(key_frame, text="Lisans Key:", font=("Consolas", 9),
                 bg=self.BG, fg=self.FG).pack(anchor="w")

        self.key_var = tk.StringVar(value="")
        self.key_entry = tk.Entry(key_frame, textvariable=self.key_var,
                                  font=("Consolas", 13), bg=self.PANEL, fg=self.GREEN,
                                  insertbackground=self.GREEN, relief=tk.FLAT, bd=0,
                                  highlightbackground=self.BORDER, highlightthickness=1,
                                  justify=tk.CENTER)
        self.key_entry.pack(fill=tk.X, pady=(4, 0), ipady=8)
        self.key_entry.focus()

        self.msg_lbl = tk.Label(self.root, text="Key girin -- otomatik dogrular",
                                font=("Consolas", 8), bg=self.BG, fg=self.FG_DIM)
        self.msg_lbl.pack(pady=(8, 0))

        self.key_var.trace("w", self._on_key_change)

    def _on_key_change(self, *args):
        if self._verifying:
            return
        key = self.key_var.get().strip()
        if len(key) >= 16:
            self._verify(key)

    def _verify(self, key):
        self._verifying = True
        self.key_entry.config(state=tk.DISABLED)
        self.msg_lbl.config(text="Dogrulanıyor...", fg=self.FG_DIM)
        threading.Thread(target=self._do_verify, args=(key,), daemon=True).start()

    def _do_verify(self, key):
        valid, username, expires, reason = verify_license(key)
        def _update():
            if valid:
                save_key(key)
                self.msg_lbl.config(text=f"Hos geldin {username}!", fg=self.GREEN)
                self.root.after(800, lambda: self.on_success(username, expires))
            else:
                self.msg_lbl.config(text=f"HATA: {reason}", fg=self.RED)
                self.key_entry.config(state=tk.NORMAL)
                self.key_var.set("")
                self.key_entry.focus()
                self._verifying = False
        self.root.after(0, _update)

# ─────────────────────────────────────────────
#  BOT İMPORTLARI
# ─────────────────────────────────────────────
import cv2
import numpy as np
import pyautogui
import pydirectinput
import time
import random
import math
from mss import mss
from pynput import keyboard

# ==================== CONFIG ====================
pyautogui.FAILSAFE = True
pydirectinput.PAUSE = 0.0   # maksimum hız — gecikme yok

sct = mss()
SW, SH = pyautogui.size()
CX, CY = SW // 2, SH // 2

WAIT_TIME = 2.6

# ==================== BÖLGE AYARLARI ====================
REGIONS = {
    "1": {
        "name": "Kızıl Orman",
        "hsv_targets": [
            {
                "name": "KizilOrman_Ana",
                "lower": np.array([0, 25, 0]),
                "upper": np.array([39, 255, 255]),
                "priority": 1,
                "min_area": 500,
                "max_area": 35000,
            }
        ],
        "description": "Kızıl Orman metinleri için optimize edilmiş ayarlar"
    },
}

# ==================== AI CONFIG ====================
AI_ENABLED = True

# ==================== THREAD-SAFE STATE ====================
_state_lock = threading.Lock()
_emergency_stop = False
_hunter_started = False

def get_emergency_stop():
    with _state_lock:
        return _emergency_stop

def set_emergency_stop(val):
    with _state_lock:
        global _emergency_stop
        _emergency_stop = val

def get_hunter_started():
    with _state_lock:
        return _hunter_started

def set_hunter_started(val):
    with _state_lock:
        global _hunter_started
        _hunter_started = val

# ==================== EXE DESTEĞI ====================
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AI_MEMORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else os.getcwd(),
    "hunter_ai_memory.json"
)

# =================================================
# NumPad- (vk=109) = başlat, NumPad0 (vk=96) = durdur

def on_press(key):
    try:
        if hasattr(key, 'vk'):
            if key.vk == 109:   # NumPad -
                set_hunter_started(True)
            elif key.vk == 96:  # NumPad 0
                set_emergency_stop(True)
    except Exception:
        pass

listener = keyboard.Listener(on_press=on_press)
listener.start()

# =================================================

class SGPRO:
    def __init__(self, region_config, gui_callback=None):
        self.region_name  = region_config["name"]
        self.hsv_targets  = sorted(region_config["hsv_targets"], key=lambda t: t["priority"])
        self.gui_callback = gui_callback

        self.sct = mss()
        # Thread-safe frame cache
        self._cache_lock  = threading.Lock()
        self._frame_cache = None
        self._cache_time  = 0

        self.log(f"SGPRO AI V12.0 | {self.region_name}")
        self.log(f"Ekran: {SW}x{SH}")
        self.log(f"HSV Hedef Sayısı: {len(self.hsv_targets)}")
        for t in self.hsv_targets:
            self.log(f"   [{t['priority']}] {t['name']} | min_alan={t['min_area']}")
        self.log("Yapay Zeka: Aktif")

        self.load_ai_memory()

        self.log("="*60)
        self.log("BEKLEME MODU")
        self.log("BAŞLATMA: NumPad - (Eksi) tuşuna basın")
        self.log("DURDURMA: NumPad 0 veya Fare (0,0)")
        self.log("="*60)

        self.stats = 0
        self.scan_count  = 0
        self.consecutive_fails = 0
        self.last_scan_center  = True

        self.last_rotation  = time.time()
        self.rotation_count = 0
        self.last_forced_q  = time.time()
        self.last_z_press   = time.time()

        self._q_lock      = threading.Lock()
        self._q_is_pressed = False

        # AI
        self.success_streak = 0
        self.fail_streak    = 0
        self.avg_response_time  = []
        self.scan_strategy  = self.ai_memory.get("preferred_strategy", "balanced")
        self.adaptive_delay = 0.02
        self.target_history = []
        self.last_successful_area = None

        self.session_start = time.time()

        self._attacking   = False
        self._collecting  = False
        self._attack_lock = threading.Lock()

        self._z_thread_stop = threading.Event()
        self._z_thread = threading.Thread(target=self._z_loop, daemon=True)
        self._z_thread.start()

    # ── q_is_pressed property (thread-safe) ──────────────────────
    @property
    def q_is_pressed(self):
        with self._q_lock:
            return self._q_is_pressed

    @q_is_pressed.setter
    def q_is_pressed(self, val):
        with self._q_lock:
            self._q_is_pressed = val

    def log(self, message):
        if self.gui_callback:
            self.gui_callback(message)
        else:
            print(message)

    # ================ AI LOGIC ================

    def load_ai_memory(self):
        if os.path.exists(AI_MEMORY_FILE):
            try:
                with open(AI_MEMORY_FILE, 'r', encoding='utf-8') as f:
                    self.ai_memory = json.load(f)
                self.log(f"AI Hafıza Yüklendi:")
                self.log(f"   Toplam Oturum: {self.ai_memory.get('total_sessions', 0)}")
                self.log(f"   Toplam Metin: {self.ai_memory.get('total_kills', 0)}")
                self.log(f"   En İyi Başarı: %{self.ai_memory.get('best_success_rate', 0):.1f}")
                self.log(f"   Tercih Edilen Strateji: {self.ai_memory.get('preferred_strategy', 'balanced').upper()}")
            except Exception as e:
                self.log(f"Hafıza dosyası okunamadı ({e}), yeni hafıza oluşturuluyor...")
                self.ai_memory = self.create_default_memory()
        else:
            self.log("Yeni AI hafızası oluşturuluyor...")
            self.ai_memory = self.create_default_memory()

    def create_default_memory(self):
        return {
            "total_sessions": 0,
            "total_kills": 0,
            "total_scans": 0,
            "best_success_rate": 0,
            "preferred_strategy": "balanced",
            "strategy_performance": {
                "aggressive": {"kills": 0, "scans": 0},
                "balanced":   {"kills": 0, "scans": 0},
                "defensive":  {"kills": 0, "scans": 0}
            },
            "avg_area": 0,
            "successful_areas": [],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def save_ai_memory(self):
        try:
            session_success_rate = (self.stats / self.scan_count * 100) if self.scan_count > 0 else 0
            self.ai_memory["total_sessions"] += 1
            self.ai_memory["total_kills"]    += self.stats
            self.ai_memory["total_scans"]    += self.scan_count

            if session_success_rate > self.ai_memory["best_success_rate"]:
                self.ai_memory["best_success_rate"] = session_success_rate

            if self.scan_strategy in self.ai_memory["strategy_performance"]:
                self.ai_memory["strategy_performance"][self.scan_strategy]["kills"] += self.stats
                self.ai_memory["strategy_performance"][self.scan_strategy]["scans"] += self.scan_count

            best_strategy = "balanced"
            best_rate = 0
            for strategy, data in self.ai_memory["strategy_performance"].items():
                if data["scans"] > 0:
                    rate = data["kills"] / data["scans"]
                    if rate > best_rate:
                        best_rate = rate
                        best_strategy = strategy
            self.ai_memory["preferred_strategy"] = best_strategy

            if self.last_successful_area:
                self.ai_memory["successful_areas"].append(self.last_successful_area)
                if len(self.ai_memory["successful_areas"]) > 20:
                    self.ai_memory["successful_areas"] = self.ai_memory["successful_areas"][-20:]
                self.ai_memory["avg_area"] = sum(self.ai_memory["successful_areas"]) // len(self.ai_memory["successful_areas"])

            self.ai_memory["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

            with open(AI_MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.ai_memory, f, indent=2, ensure_ascii=False)

            self.log(f"AI Hafıza Kaydedildi: {AI_MEMORY_FILE}")
        except Exception as e:
            self.log(f"Hafıza kaydedilemedi: {e}")

    def ai_adjust_strategy(self):
        if not AI_ENABLED:
            return
        if self.scan_count > 10:
            success_rate = self.stats / self.scan_count
            historical_preference = self.ai_memory.get("preferred_strategy", "balanced")
            if success_rate > 0.7:
                self.scan_strategy  = "aggressive"
                self.adaptive_delay = 0.005   # 0.01 → 0.005
            elif success_rate < 0.3:
                self.scan_strategy  = "defensive"
                self.adaptive_delay = 0.01    # 0.03 → 0.01
            else:
                self.scan_strategy  = historical_preference
                self.adaptive_delay = 0.008   # 0.02 → 0.008

    def ai_smart_rotation(self):
        if self.fail_streak > 3:
            return (2.0, 0.4)
        elif self.success_streak > 5:
            return (4.0, 0.2)
        else:
            return (3.0, 0.3)

    def _z_loop(self):
        """En hızlı \" (tırnak) basma — q/attack/collect sırasında dur, aralık 0.05s."""
        COLLECT_KEY = '"'
        while not self._z_thread_stop.is_set() and not get_emergency_stop():
            if not self.q_is_pressed and not self._attacking and not self._collecting:
                try:
                    pydirectinput.keyDown(COLLECT_KEY)
                    time.sleep(0.015)
                    pydirectinput.keyUp(COLLECT_KEY)
                except Exception:
                    try:
                        pyautogui.keyDown(COLLECT_KEY)
                        time.sleep(0.015)
                        pyautogui.keyUp(COLLECT_KEY)
                    except Exception as e:
                        self.log(f'" tusu hatasi: {e}')
            # 0.05s aralık
            for _ in range(5):
                if self._z_thread_stop.is_set() or get_emergency_stop():
                    return
                time.sleep(0.01)


    # ================ UTILS ================

    def get_mask(self, roi, hsv_target):
        """Verilen HSV hedefi için maske oluştur — gürültü temizleme dahil"""
        hsv  = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, hsv_target["lower"], hsv_target["upper"])
        k    = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k)   # gürültü temizle
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)   # delikleri kapat
        mask = cv2.dilate(mask, k, iterations=1)             # kenarları genişlet
        return mask

    def capture(self):
        now = time.time()
        with self._cache_lock:
            if self._frame_cache is None or now - self._cache_time > 0.09:
                monitor = {"top": 0, "left": 0, "width": SW, "height": SH}
                img = np.array(self.sct.grab(monitor))
                self._frame_cache = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                self._cache_time  = now
            return self._frame_cache.copy()

    # ================ TARGET ================

    def find_targets_for_hsv(self, roi, ox, oy, hsv_target):
        """Tek bir HSV hedefi için aday listesi döndür"""
        min_area = hsv_target["min_area"]
        max_area = hsv_target["max_area"]

        mask = self.get_mask(roi, hsv_target)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area or area > max_area:
                continue

            x, y, w, h = cv2.boundingRect(c)
            if w < 16 or h < 16:
                continue

            aspect = w / h
            if aspect < 0.4 or aspect > 2.4:
                continue

            hull      = cv2.convexHull(c)
            hull_area = cv2.contourArea(hull)
            if hull_area == 0:
                continue

            solidity = area / hull_area
            if solidity < 0.45:
                continue

            cx   = ox + x + w // 2
            cy   = oy + y + h // 2
            dist = math.hypot(cx - CX, cy - CY)

            # Karakter merkezini yoksay
            if dist < 60:
                continue

            # Çok uzak hedefleri yoksay
            if dist > 500:
                continue

            # AI: benzer alana öncelik
            priority_bonus = 0
            if self.last_successful_area and abs(area - self.last_successful_area) < 500:
                priority_bonus = -100
            elif self.ai_memory.get("avg_area", 0) > 0 and abs(area - self.ai_memory["avg_area"]) < 500:
                priority_bonus = -50

            candidates.append((cx, cy, dist + priority_bonus, area, solidity, w, h))

        return candidates

    def find_target(self):
        frame = self.capture()
        self.scan_count += 1

        # Strateji bazlı tarama alanı
        if self.scan_strategy == "aggressive":
            roi = frame[int(SH*0.2):int(SH*0.8), int(SW*0.2):int(SW*0.8)]
            ox, oy = int(SW*0.2), int(SH*0.2)
            mode = "AGRESIF"
        elif self.scan_strategy == "defensive":
            roi = frame[int(SH*0.35):int(SH*0.65), int(SW*0.35):int(SW*0.65)]
            ox, oy = int(SW*0.35), int(SH*0.35)
            mode = "DEFANSIF"
        else:
            if self.last_scan_center:
                roi = frame[int(SH*0.3):int(SH*0.7), int(SW*0.3):int(SW*0.7)]
                ox, oy = int(SW*0.3), int(SH*0.3)
                mode = "MERKEZ"
            else:
                roi = frame[int(SH*0.1):int(SH*0.9), int(SW*0.1):int(SW*0.9)]
                ox, oy = int(SW*0.1), int(SH*0.1)
                mode = "KENAR"

        self.log(f"#{self.scan_count} - {mode} [{self.scan_strategy.upper()}] | {len(self.hsv_targets)} HSV taranıyor")

        # ── ÇOKLU HSV TARAMA ──
        # Öncelik sırasına göre her HSV'yi dene, ilk bulunanı döndür
        for hsv_target in self.hsv_targets:
            candidates = self.find_targets_for_hsv(roi, ox, oy, hsv_target)

            if candidates:
                best_5 = sorted(candidates, key=lambda t: (t[2], -t[3], -t[4]))[:5]
                self.log(f"   ✓ [{hsv_target['priority']}] {hsv_target['name']} → {len(candidates)} aday")
                self.consecutive_fails = 0
                self.fail_streak       = 0
                self.success_streak   += 1
                self.last_scan_center  = not self.last_scan_center
                self.ai_adjust_strategy()
                return best_5, hsv_target["name"]
            else:
                self.log(f"   ✗ [{hsv_target['priority']}] {hsv_target['name']} → bulunamadı")

        # Hiçbir HSV'de bulunamadı
        self.consecutive_fails += 1
        self.fail_streak       += 1
        self.success_streak     = 0
        self.last_scan_center   = not self.last_scan_center
        self.ai_adjust_strategy()
        return None, None

    # ================ ACTION ================

    def attack(self, targets, target_name=""):
        self._attacking = True
        try:
            import ctypes
            MOUSEEVENTF_RIGHTDOWN = 0x0008
            MOUSEEVENTF_RIGHTUP   = 0x0010
            VK_SHIFT = 0x10

            def _fast_shift_rclick(n):
                """Shift basılıyken n kez sağ click — kaçırma olmadan, çakışmasız."""
                ctypes.windll.user32.keybd_event(VK_SHIFT, 0, 0, 0)   # shift down
                time.sleep(0.008)  # shift'in oyun tarafından algılanması için
                for _ in range(n):
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP,   0, 0, 0, 0)
                    time.sleep(0.005)  # her click arası 5ms — oyun engine kaçırmasın
                ctypes.windll.user32.keybd_event(VK_SHIFT, 0, 0x0002, 0)  # shift up

            for t in targets:
                x, y, dist, area, solidity, w, h = t
                self.log(f"HEDEF #{self.stats+1} [{target_name}]: {int(abs(dist))}px | {w}x{h} | solid:{solidity:.2f}")

                self.target_history.append((x, y))
                if len(self.target_history) > 10:
                    self.target_history.pop(0)

                self.last_successful_area = area

                move_time = 0 if abs(dist) < 250 else 0.02
                click_y   = y + int(h * 0.2)

                try:
                    pydirectinput.moveTo(x, click_y, duration=move_time)
                    _fast_shift_rclick(12)   # 12 click — kaçırma yok
                except Exception as e:
                    self.log(f"Win32 hatasi, pydirectinput fallback: {e}")
                    try:
                        pydirectinput.moveTo(x, click_y, duration=move_time)
                        pydirectinput.keyDown("shift")
                        for _ in range(12):
                            pydirectinput.rightClick()
                            time.sleep(0.005)
                        pydirectinput.keyUp("shift")
                    except Exception as e2:
                        self.log(f"pydirectinput da basarisiz: {e2}")

                self.stats += 1

                # Tas kirildi — itemleri garantili topla
                self._collect_loot()

            time.sleep(random.uniform(0.02, 0.05))
        finally:
            self._attacking = False

    def _collect_loot(self):
        """Taş kırıldıktan sonra düşen itemleri topla — garantili, çakışmasız."""
        self._collecting = True   # z_loop'u durdur
        try:
            time.sleep(0.25)
            self.log('   -> Item toplanıyor (")')
            COLLECT_KEY = '"'
            for _ in range(6):
                try:
                    pydirectinput.keyDown(COLLECT_KEY)
                    time.sleep(0.012)
                    pydirectinput.keyUp(COLLECT_KEY)
                except Exception:
                    try:
                        pyautogui.keyDown(COLLECT_KEY)
                        time.sleep(0.012)
                        pyautogui.keyUp(COLLECT_KEY)
                    except Exception:
                        pass
                time.sleep(0.03)
        finally:
            self._collecting = False   # z_loop'u serbest bırak

    # ================ MAIN LOOP ================

    def _press_key(self, key, duration):
        """Bir tuşa basıp bırak — pydirectinput > pyautogui fallback"""
        try:
            pydirectinput.keyDown(key)
            time.sleep(duration)
            pydirectinput.keyUp(key)
        except Exception as e:
            self.log(f"pydirectinput hatası ({key}): {e}")
            try:
                pyautogui.keyDown(key)
                time.sleep(duration)
                pyautogui.keyUp(key)
            except Exception as e2:
                self.log(f"pyautogui da başarısız ({key}): {e2}")

    def run(self):
        self.log("NumPad - (Eksi) tuşuna basarak başlatın...")

        while not get_hunter_started():
            time.sleep(0.1)
            if get_emergency_stop():
                self.log("Program iptal edildi.")
                return

        self.log(f"{self.region_name} TARAYICI BAŞLADI!")
        self.log("Oyuna geçebilirsiniz...")
        time.sleep(2)

        try:
            while True:
                if pyautogui.position() == (0, 0):
                    self.log("Acil durdurma (fare)")
                    break

                if get_emergency_stop():
                    self.log("Acil durdurma (NumPad 0)")
                    break

                now = time.time()

                # Zorunlu Q
                if now - self.last_forced_q >= 15:
                    self.log("Zorunlu Q (1.5s)")
                    self.q_is_pressed = True
                    self._press_key("q", 1.5)
                    self.q_is_pressed = False
                    self.last_forced_q = time.time()
                    self.last_z_press  = time.time()

                targets, target_name = self.find_target()
                if targets:
                    self.attack(targets, target_name)
                else:
                    time.sleep(random.uniform(0.03, 0.08))

                # Rotasyon
                rotation_interval, rotation_duration = self.ai_smart_rotation()
                if now - self.last_rotation > rotation_interval:
                    key = random.choice(["q", "e"])
                    self.q_is_pressed = (key == "q")
                    self._press_key(key, rotation_duration)
                    self.q_is_pressed = False
                    self.last_rotation = time.time()
                    self.rotation_count += 1
                    if key == "q":
                        self.last_z_press = time.time()

                time.sleep(self.adaptive_delay)

        finally:
            self._z_thread_stop.set()
            session_time = time.time() - self.session_start
            self.log("=" * 60)
            self.log(f"{self.region_name} - OTURUM İSTATİSTİKLERİ")
            self.log("=" * 60)
            self.log(f"Toplam Metin: {self.stats}")
            self.log(f"Toplam Tarama: {self.scan_count}")
            if self.scan_count:
                self.log(f"Başarı Oranı: {(self.stats/self.scan_count)*100:.1f}%")
            self.log(f"Son Strateji: {self.scan_strategy.upper()}")
            self.log(f"Başarı Serisi: {self.success_streak}")
            self.log(f"Oturum Süresi: {int(session_time//60)}dk {int(session_time%60)}sn")
            self.log("=" * 60)
            self.save_ai_memory()


# ================ GUI ================

class SGPROGUI:
    def __init__(self, root, username="", expires=""):
        self.root     = root
        self.username = username
        self.expires  = expires
        self.root.title("SGPRO — Kızıl Orman")
        self.root.geometry("420x430")
        self.root.resizable(False, False)

        self.BG     = "#0a0a0a"
        self.PANEL  = "#111111"
        self.BORDER = "#222222"
        self.TEXT   = "#f0f0f0"
        self.MUTED  = "#444444"
        self.ACCENT = "#ff6b35"   # Kızıl Orman rengi
        self.GREEN  = "#00d26a"
        self.RED    = "#ff4757"
        self.CYAN   = "#58a6ff"

        self.root.configure(bg=self.BG)
        self.running = False
        self._active_hunter = None

        self._build()
        self._start_license_watchdog()

    def _sep(self, parent, color=None):
        tk.Frame(parent, bg=color or self.BORDER, height=1).pack(fill="x")

    def _build(self):
        # ── TOP BAR ─────────────────────────────────────────────
        tk.Frame(self.root, bg=self.ACCENT, height=3).pack(fill="x")

        # ── HEADER ──────────────────────────────────────────────
        header = tk.Frame(self.root, bg=self.BG)
        header.pack(fill="x", padx=20, pady=(12, 10))

        left = tk.Frame(header, bg=self.BG)
        left.pack(side="left")
        tk.Label(left, text="SGPRO",
                 font=("Segoe UI", 20, "bold"),
                 fg=self.ACCENT, bg=self.BG).pack(anchor="w")
        tk.Label(left, text="SGPRO  ·  V12.0  ·  Kızıl Orman",
                 font=("Segoe UI", 7),
                 fg=self.MUTED, bg=self.BG).pack(anchor="w")

        # Kullanıcı + kalan gün
        def _calc_days(exp_str):
            if not exp_str or exp_str == "Sınırsız":
                return "Sinirsiz"
            try:
                from datetime import datetime
                exp   = datetime.strptime(exp_str, "%d.%m.%Y")
                delta = (exp - datetime.now()).days
                if delta < 0:    return "Suresi doldu"
                elif delta == 0: return "Son gun!"
                else:            return f"{delta} gun kaldi"
            except:
                return exp_str
        days_left = _calc_days(self.expires)
        day_color = self.RED if "doldu" in days_left or "Son gun" in days_left else self.CYAN
        tk.Label(left, text=f"Kullanici: {self.username}   {days_left}",
                 font=("Segoe UI", 8, "bold"),
                 fg=day_color, bg=self.BG).pack(anchor="w")

        right = tk.Frame(header, bg=self.BG)
        right.pack(side="right")
        badge = tk.Frame(right, bg=self.ACCENT, padx=8, pady=3)
        badge.pack()
        tk.Label(badge, text="● ONLINE",
                 font=("Segoe UI", 7, "bold"),
                 fg=self.BG, bg=self.ACCENT).pack()

        self._sep(self.root)

        # ── HARİTA BİLGİSİ ──────────────────────────────────────
        info = tk.Frame(self.root, bg="#1c0a05", padx=16, pady=12)
        info.pack(fill="x", padx=20, pady=10)

        tk.Frame(info, bg=self.ACCENT, width=3).pack(side="left", fill="y")
        ic = tk.Frame(info, bg="#1c0a05")
        ic.pack(side="left", padx=10)
        tk.Label(ic, text="🔥  KIZIL ORMAN",
                 font=("Segoe UI", 11, "bold"),
                 fg=self.ACCENT, bg="#1c0a05").pack(anchor="w")
        tk.Label(ic, text="HSV Optimize  ·  Otomatik AI Strateji",
                 font=("Segoe UI", 7),
                 fg=self.MUTED, bg="#1c0a05").pack(anchor="w")

        self._sep(self.root)

        # ── KONTROL ─────────────────────────────────────────────
        ctrl = tk.Frame(self.root, bg=self.BG, padx=20, pady=10)
        ctrl.pack(fill="x")

        self.start_button = tk.Button(
            ctrl, text="▶   BAŞLAT   ( NumPad − )",
            font=("Segoe UI", 10, "bold"),
            bg=self.GREEN, fg="#000000",
            activebackground="#00b359", activeforeground="#000000",
            relief="flat", bd=0, cursor="hand2", height=2,
            command=self.start_hunter
        )
        self.start_button.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.stop_button = tk.Button(
            ctrl, text="■   DURDUR   ( NumPad 0 )",
            font=("Segoe UI", 10, "bold"),
            bg=self.BORDER, fg=self.MUTED,
            activebackground=self.RED, activeforeground="#ffffff",
            relief="flat", bd=0, cursor="hand2", height=2,
            state=tk.DISABLED,
            command=self.stop_hunter
        )
        self.stop_button.pack(side="left", fill="x", expand=True, padx=(6, 0))

        self._sep(self.root)

        # ── DURUM ───────────────────────────────────────────────
        sbar = tk.Frame(self.root, bg=self.PANEL, pady=5)
        sbar.pack(fill="x", padx=20)

        self.dot = tk.Label(sbar, text="◉", font=("Segoe UI", 10),
                            fg=self.MUTED, bg=self.PANEL)
        self.dot.pack(side="left")
        self.status_label = tk.Label(sbar,
                                     text="  HAZIR — BAŞLAT'a bas",
                                     font=("Segoe UI", 8),
                                     fg=self.TEXT, bg=self.PANEL, anchor="w")
        self.status_label.pack(side="left")

        # ── LOG ─────────────────────────────────────────────────
        log_wrap = tk.Frame(self.root, bg=self.BORDER, padx=1, pady=1)
        log_wrap.pack(fill="both", expand=True, padx=20, pady=(8, 4))

        log_inner = tk.Frame(log_wrap, bg=self.PANEL)
        log_inner.pack(fill="both", expand=True)

        lhdr = tk.Frame(log_inner, bg=self.PANEL, pady=4)
        lhdr.pack(fill="x", padx=8)
        tk.Frame(lhdr, bg=self.ACCENT, width=3, height=10).pack(side="left")
        tk.Label(lhdr, text="  / LOG",
                 font=("Segoe UI", 7, "bold"),
                 fg=self.ACCENT, bg=self.PANEL).pack(side="left")

        tk.Frame(log_inner, bg=self.BORDER, height=1).pack(fill="x")

        self.log_text = scrolledtext.ScrolledText(
            log_inner, font=("Consolas", 7),
            bg="#080808", fg=self.GREEN,
            insertbackground=self.ACCENT,
            height=6, wrap=tk.WORD,
            state=tk.DISABLED, relief="flat", bd=0
        )
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

        # ── FOOTER ──────────────────────────────────────────────
        self._sep(self.root)
        tk.Label(self.root,
                 text="NumPad −  başlat    NumPad 0  durdur    Fare(0,0)  acil durdur",
                 font=("Segoe UI", 6), fg=self.MUTED, bg=self.BG, pady=4).pack()

    def log_message(self, message):
        def _do():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def _set_status(self, text, color):
        self.status_label.configure(text=f"  {text}")
        self.dot.configure(fg=color)

    def start_hunter(self):
        if self.running:
            messagebox.showwarning("Uyarı", "Hunter zaten çalışıyor!")
            return

        set_hunter_started(False)
        set_emergency_stop(False)
        selected_region = REGIONS["1"]

        self.log_message("─" * 40)
        self.log_message(f"  BAŞLATILIYOR  ·  {selected_region['name']}")
        self.log_message("─" * 40)

        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL, bg=self.RED, fg="#ffffff")
        self._set_status("ÇALIŞIYOR  ·  Kızıl Orman  ·  NumPad − ile başlat", self.GREEN)

        def run_hunter():
            try:
                hunter = SGPRO(selected_region, self.log_message)
                self._active_hunter = hunter
                hunter.run()
            except Exception as e:
                import traceback
                self.log_message(f"HATA: {e}")
                self.log_message(traceback.format_exc())
            finally:
                self._active_hunter = None
            try:
                self.root.after(0, self.on_hunter_finished)
            except Exception:
                pass

        self.hunter_thread = threading.Thread(target=run_hunter, daemon=True)
        self.hunter_thread.start()

    def on_hunter_finished(self):
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED, bg=self.BORDER, fg=self.MUTED)
        self._set_status("TAMAMLANDI — Yeni oturum için BAŞLAT'a bas", self.MUTED)
        self.running = False

    def stop_hunter(self):
        if not self.running:
            return
        set_emergency_stop(True)
        # Aktif hunter thread'indeki z döngüsünü de durdur
        if hasattr(self, '_active_hunter') and self._active_hunter:
            self._active_hunter._z_thread_stop.set()
        self.log_message("─" * 40)
        self.log_message("  DURDURULDU")
        self.log_message("─" * 40)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED, bg=self.BORDER, fg=self.MUTED)
        self._set_status("DURDURULDU", self.RED)
        self.running = False

    # ── LİSANS PERİYODİK KONTROL ──
    def _start_license_watchdog(self):
        def _watchdog():
            import time as _time
            _time.sleep(10)  # ilk kontrol 10 saniye sonra
            while True:
                try:
                    saved = load_saved_key()
                    if saved:
                        valid, _, _, _ = verify_license(saved)
                        if not valid:
                            def _expired():
                                import os
                                os._exit(0)
                            self.root.after(0, _expired)
                            return
                except Exception:
                    pass
                _time.sleep(10)  # her 10 saniyede bir kontrol
        threading.Thread(target=_watchdog, daemon=True).start()


# ================ MAIN ================

def main():
    root = tk.Tk()

    def after_license(username="", expires=""):
        for w in root.winfo_children():
            w.destroy()
        SGPROGUI(root, username=username, expires=expires)

    saved_key = load_saved_key()
    if saved_key:
        # Kayitli key var -- otomatik dogrula
        root.configure(bg="#0d0f14")
        root.title("SGPRO")
        root.geometry("420x200")
        root.resizable(False, False)
        tk.Label(root, text="SGPRO",
                 font=("Consolas", 28, "bold"),
                 bg="#0d0f14", fg="#39d353").pack(expand=True)
        tk.Label(root, text="Dogrulanıyor...",
                 font=("Consolas", 10),
                 bg="#0d0f14", fg="#6e7681").pack()

        def _auto_verify():
            valid, username, expires, reason = verify_license(saved_key)
            if valid:
                root.after(0, lambda: after_license(username, expires))
            else:
                def _show():
                    for w in root.winfo_children():
                        w.destroy()
                    LicenseScreen(root, on_success=after_license)
                root.after(0, _show)

        threading.Thread(target=_auto_verify, daemon=True).start()
    else:
        LicenseScreen(root, on_success=after_license)

    root.mainloop()

if __name__ == "__main__":
    main()
