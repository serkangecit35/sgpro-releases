#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MadenBot Admin Panel
Sadece sende olacak — kullanıcıları buradan yönetirsin.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import requests
import threading
import json

# ══════════════════════════════════════════
#  AYARLAR — Render'a yükleyince URL'yi güncelle
# ══════════════════════════════════════════
API_URL      = "https://madenbot-server.onrender.com"   # ← buraya Render URL'ini yaz
ADMIN_SECRET = "madenbot2024"                      # ← backend'deki ile aynı olmalı

HEADERS = {"X-Admin-Secret": ADMIN_SECRET, "Content-Type": "application/json"}

# ══════════════════════════════════════════
#  RENKLER
# ══════════════════════════════════════════
BG        = "#0d0f14"
PANEL     = "#161b22"
BORDER    = "#30363d"
GREEN     = "#39d353"
GREEN_DIM = "#1a6b2a"
RED       = "#f85149"
YELLOW    = "#e3b341"
CYAN      = "#58a6ff"
FG        = "#c9d1d9"
FG_DIM    = "#6e7681"

# ══════════════════════════════════════════
#  API YARDIMCILARI
# ══════════════════════════════════════════
def api(method, endpoint, **kwargs):
    try:
        r = requests.request(method, API_URL + endpoint, headers=HEADERS, timeout=8, **kwargs)
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Sunucuya bağlanılamadı"}
    except Exception as e:
        return {"error": str(e)}

# ══════════════════════════════════════════
#  ANA UYGULAMA
# ══════════════════════════════════════════
class AdminApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🔑 MadenBot Admin Panel")
        self.root.geometry("1000x620")
        self.root.resizable(True, True)
        self.root.configure(bg=BG)
        self.root.minsize(800, 500)

        self._build_ui()
        self._refresh()

    def _build_ui(self):
        # ── Başlık ──
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill=tk.X, padx=20, pady=(16, 0))

        tk.Label(hdr, text="🔑  MADENBOT ADMİN PANELİ",
                 font=("Consolas", 14, "bold"), bg=BG, fg=GREEN).pack(side=tk.LEFT)

        self.status_lbl = tk.Label(hdr, text="● Bağlı",
                                   font=("Consolas", 9), bg=BG, fg=GREEN)
        self.status_lbl.pack(side=tk.RIGHT)

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X, padx=20, pady=10)

        # ── Toolbar ──
        tb = tk.Frame(self.root, bg=BG)
        tb.pack(fill=tk.X, padx=20, pady=(0, 8))

        btn_cfg = dict(font=("Consolas", 9, "bold"), relief=tk.FLAT, bd=0,
                       padx=14, pady=7, cursor="hand2")

        tk.Button(tb, text="＋  Kullanıcı Ekle", bg=GREEN_DIM, fg=GREEN,
                  activebackground=GREEN, activeforeground="#000",
                  command=self._add_user, **btn_cfg).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(tb, text="🔄  Yenile", bg=PANEL, fg=FG,
                  activebackground=BORDER, activeforeground=FG,
                  command=self._refresh, **btn_cfg).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(tb, text="⏳  Süre Uzat", bg="#1a1a2a", fg=CYAN,
                  activebackground=CYAN, activeforeground="#000",
                  command=self._extend, **btn_cfg).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(tb, text="🔁  HWID Sıfırla", bg="#1a1a14", fg=YELLOW,
                  activebackground=YELLOW, activeforeground="#000",
                  command=self._reset_hwid, **btn_cfg).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(tb, text="⏸  Askıya Al / Aktif Et", bg="#1a1414", fg=YELLOW,
                  activebackground=YELLOW, activeforeground="#000",
                  command=self._toggle, **btn_cfg).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(tb, text="🗑  Sil", bg="#2d1515", fg=RED,
                  activebackground=RED, activeforeground="#000",
                  command=self._delete, **btn_cfg).pack(side=tk.LEFT)

        tk.Button(tb, text="🚀  Güncelleme Yayınla", bg="#0d1a0d", fg=GREEN,
                  activebackground=GREEN, activeforeground="#000",
                  command=self._set_version, **btn_cfg).pack(side=tk.RIGHT)

        # ── Tablo ──
        tbl_frame = tk.Frame(self.root, bg=PANEL,
                             highlightbackground=BORDER, highlightthickness=1)
        tbl_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        cols = ("Kullanıcı", "Key", "Plan", "Durum", "Bitiş", "Son Görülme", "HWID")
        self.tree = ttk.Treeview(tbl_frame, columns=cols, show="headings", height=18)

        widths = [130, 160, 80, 80, 110, 140, 120]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                         background=PANEL, fieldbackground=PANEL,
                         foreground=FG, rowheight=28,
                         font=("Consolas", 9))
        style.configure("Treeview.Heading",
                         background=BG, foreground=FG_DIM,
                         font=("Consolas", 9, "bold"))
        style.map("Treeview", background=[("selected", "#1f3040")])

        self.tree.tag_configure("valid",    foreground=GREEN)
        self.tree.tag_configure("expired",  foreground=RED)
        self.tree.tag_configure("inactive", foreground=FG_DIM)

        sb = ttk.Scrollbar(tbl_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # ── Alt bilgi ──
        self.info_lbl = tk.Label(self.root, text="",
                                 font=("Consolas", 8), bg=BG, fg=FG_DIM)
        self.info_lbl.pack(pady=(0, 10))

    # ── VERİ YÜKLEME ──
    def _refresh(self):
        self.status_lbl.config(text="● Yükleniyor…", fg=YELLOW)
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        data = api("GET", "/admin/list")
        def _update():
            self.tree.delete(*self.tree.get_children())
            if "error" in data:
                self.status_lbl.config(text=f"✗ {data['error']}", fg=RED)
                return
            for lic in data:
                tag = lic["status"]  # valid / expired / inactive
                self.tree.insert("", tk.END, iid=str(lic["id"]), values=(
                    lic["username"],
                    lic["key"],
                    lic["plan"],
                    {"valid": "✅ Aktif", "expired": "❌ Süresi doldu",
                     "inactive": "⏸ Askıda"}.get(lic["status"], lic["status"]),
                    lic["expires_at"],
                    lic["last_seen"],
                    lic["hwid"],
                ), tags=(tag,))
            total   = len(data)
            active  = sum(1 for l in data if l["status"] == "valid")
            expired = sum(1 for l in data if l["status"] == "expired")
            self.status_lbl.config(text="● Bağlı", fg=GREEN)
            self.info_lbl.config(
                text=f"Toplam: {total}  |  Aktif: {active}  |  Süresi Dolmuş: {expired}")
        self.root.after(0, _update)

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Seçim", "Lütfen bir kullanıcı seçin.")
            return None
        return int(sel[0])

    # ── KULLANICI EKLE ──
    def _add_user(self):
        win = tk.Toplevel(self.root)
        win.title("Kullanıcı Ekle")
        win.geometry("360x300")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        def row(label, default=""):
            f = tk.Frame(win, bg=BG)
            f.pack(fill=tk.X, padx=20, pady=6)
            tk.Label(f, text=label, font=("Consolas", 9), bg=BG, fg=FG,
                     width=18, anchor="w").pack(side=tk.LEFT)
            sv = tk.StringVar(value=default)
            tk.Entry(f, textvariable=sv, font=("Consolas", 9), bg=PANEL, fg=GREEN,
                     insertbackground=GREEN, relief=tk.FLAT, bd=1,
                     highlightbackground=BORDER, highlightthickness=1).pack(side=tk.RIGHT, fill=tk.X, expand=True)
            return sv

        tk.Label(win, text="Yeni Kullanıcı", font=("Consolas", 11, "bold"),
                 bg=BG, fg=GREEN).pack(pady=(16, 8))

        name_var = row("Kullanıcı Adı")
        sure_var = row("Süre", "30")

        # Birim seçimi: Dakika / Saat / Gün / Ay
        birim_var = tk.StringVar(value="gun")
        bf = tk.Frame(win, bg=BG)
        bf.pack(fill=tk.X, padx=20, pady=4)
        tk.Label(bf, text="Birim", font=("Consolas", 9), bg=BG, fg=FG,
                 width=18, anchor="w").pack(side=tk.LEFT)
        for val, txt in [("dakika", "Dakika"), ("saat", "Saat"), ("gun", "Gün"), ("ay", "Ay")]:
            tk.Radiobutton(bf, text=txt, variable=birim_var, value=val,
                           font=("Consolas", 9), bg=BG, fg=FG,
                           selectcolor=BG, activebackground=BG).pack(side=tk.LEFT, padx=4)

        plan_var = tk.StringVar(value="monthly")
        pf = tk.Frame(win, bg=BG)
        pf.pack(fill=tk.X, padx=20, pady=6)
        tk.Label(pf, text="Plan", font=("Consolas", 9), bg=BG, fg=FG,
                 width=18, anchor="w").pack(side=tk.LEFT)
        for val, txt in [("monthly", "Aylık"), ("lifetime", "Sınırsız")]:
            tk.Radiobutton(pf, text=txt, variable=plan_var, value=val,
                           font=("Consolas", 9), bg=BG, fg=FG,
                           selectcolor=BG, activebackground=BG).pack(side=tk.LEFT, padx=6)

        def _submit():
            username = name_var.get().strip()
            plan     = plan_var.get()
            birim    = birim_var.get()
            try:
                miktar = float(sure_var.get())
            except:
                miktar = 1.0
            # Güne çevir (float destekli)
            if birim == "dakika":
                days = miktar / 1440.0
            elif birim == "saat":
                days = miktar / 24.0
            elif birim == "ay":
                days = miktar * 30.0
            else:  # gun
                days = miktar
            if not username:
                messagebox.showerror("Hata", "Kullanıcı adı boş olamaz.", parent=win)
                return
            result = api("POST", "/admin/create",
                         json={"username": username, "plan": plan, "days": days})
            if "error" in result:
                messagebox.showerror("Hata", result["error"], parent=win)
            else:
                win.destroy()
                self._refresh()
                # Kopyalanabilir key penceresi
                kwin = tk.Toplevel(self.root)
                kwin.title("✅ Key Oluşturuldu")
                kwin.geometry("380x220")
                kwin.configure(bg=BG)
                kwin.resizable(False, False)
                kwin.grab_set()

                tk.Label(kwin, text="✅  Key Oluşturuldu!",
                         font=("Consolas", 12, "bold"), bg=BG, fg=GREEN).pack(pady=(20, 4))
                tk.Label(kwin, text=f"Kullanıcı: {result['username']}  |  Bitiş: {result['expires']}",
                         font=("Consolas", 9), bg=BG, fg=FG_DIM).pack()

                tk.Frame(kwin, bg=BORDER, height=1).pack(fill=tk.X, padx=20, pady=12)

                tk.Label(kwin, text="Lisans Key:", font=("Consolas", 9),
                         bg=BG, fg=FG).pack(anchor="w", padx=24)

                key_var = tk.StringVar(value=result['key'])
                key_entry = tk.Entry(kwin, textvariable=key_var,
                                     font=("Consolas", 13, "bold"),
                                     bg=PANEL, fg=GREEN,
                                     insertbackground=GREEN,
                                     relief=tk.FLAT, bd=0,
                                     highlightbackground=GREEN,
                                     highlightthickness=1,
                                     justify=tk.CENTER,
                                     state="readonly")
                key_entry.pack(fill=tk.X, padx=24, pady=(4, 0), ipady=8)

                def _copy():
                    kwin.clipboard_clear()
                    kwin.clipboard_append(result['key'])
                    copy_btn.config(text="✅  Kopyalandı!", fg=GREEN)
                    kwin.after(2000, lambda: copy_btn.config(text="📋  Key'i Kopyala", fg=CYAN))

                copy_btn = tk.Button(kwin, text="📋  Key'i Kopyala",
                                     font=("Consolas", 10, "bold"),
                                     bg="#0d1a2a", fg=CYAN,
                                     activebackground=CYAN, activeforeground="#000",
                                     relief=tk.FLAT, bd=0, padx=16, pady=8,
                                     cursor="hand2", command=_copy)
                copy_btn.pack(pady=14)

                tk.Button(kwin, text="Kapat", font=("Consolas", 8),
                          bg=PANEL, fg=FG_DIM, relief=tk.FLAT, bd=0,
                          cursor="hand2", command=kwin.destroy).pack()

        tk.Button(win, text="✅  Oluştur", font=("Consolas", 10, "bold"),
                  bg=GREEN_DIM, fg=GREEN, activebackground=GREEN, activeforeground="#000",
                  relief=tk.FLAT, bd=0, padx=20, pady=8, cursor="hand2",
                  command=_submit).pack(pady=12)

    # ── SİL ──
    def _delete(self):
        uid = self._selected_id()
        if uid is None:
            return
        name = self.tree.item(str(uid))["values"][0]
        if not messagebox.askyesno("Sil", f"'{name}' silinsin mi?"):
            return
        result = api("POST", "/admin/delete", json={"id": uid})
        if "error" in result:
            messagebox.showerror("Hata", result["error"])
        else:
            self._refresh()

    # ── ASKIYA AL / AKTİF ET ──
    def _toggle(self):
        uid = self._selected_id()
        if uid is None:
            return
        result = api("POST", "/admin/toggle", json={"id": uid})
        if "error" in result:
            messagebox.showerror("Hata", result["error"])
        else:
            self._refresh()

    # ── SÜRE UZAT ──
    def _extend(self):
        uid = self._selected_id()
        if uid is None:
            return
        days = simpledialog.askinteger("Süre Uzat", "Kaç gün eklensin?",
                                       minvalue=1, maxvalue=3650, initialvalue=30)
        if not days:
            return
        result = api("POST", "/admin/extend", json={"id": uid, "days": days})
        if "error" in result:
            messagebox.showerror("Hata", result["error"])
        else:
            messagebox.showinfo("✅", f"Yeni bitiş: {result['expires']}")
            self._refresh()

    # ── GÜNCELLEME YAYINLA ──
    def _set_version(self):
        win = tk.Toplevel(self.root)
        win.title("Guncelleme Yayinla")
        win.geometry("460x240")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Guncelleme Yayinla",
                 font=("Consolas", 11, "bold"), bg=BG, fg=GREEN).pack(pady=(18, 4))
        tk.Label(win, text="Botlar acilinca otomatik indirir",
                 font=("Consolas", 8), bg=BG, fg=FG_DIM).pack()
        tk.Frame(win, bg=BORDER, height=1).pack(fill=tk.X, padx=20, pady=10)

        def row(label, default=""):
            f = tk.Frame(win, bg=BG)
            f.pack(fill=tk.X, padx=20, pady=5)
            tk.Label(f, text=label, font=("Consolas", 9), bg=BG, fg=FG,
                     width=14, anchor="w").pack(side=tk.LEFT)
            sv = tk.StringVar(value=default)
            tk.Entry(f, textvariable=sv, font=("Consolas", 9), bg=PANEL, fg=GREEN,
                     insertbackground=GREEN, relief=tk.FLAT, bd=1,
                     highlightbackground=BORDER, highlightthickness=1).pack(side=tk.RIGHT, fill=tk.X, expand=True)
            return sv

        ver_var = row("Yeni Versiyon", "1.1")
        url_var = row("EXE Indirme Linki", "https://github.com/...")

        def _submit():
            ver = ver_var.get().strip()
            url = url_var.get().strip()
            if not ver or not url or url == "https://github.com/...":
                messagebox.showerror("Hata", "Versiyon ve gecerli bir link girin.", parent=win)
                return
            result = api("POST", "/admin/set_version", json={"version": ver, "url": url})
            if "error" in result:
                messagebox.showerror("Hata", result["error"], parent=win)
            else:
                win.destroy()
                messagebox.showinfo("Tamam", f"Versiyon {ver} yayinlandi!\nBotlar acilinca otomatik guncellenir.")

        tk.Button(win, text="Yayinla", font=("Consolas", 10, "bold"),
                  bg=GREEN_DIM, fg=GREEN, activebackground=GREEN, activeforeground="#000",
                  relief=tk.FLAT, bd=0, padx=20, pady=8, cursor="hand2",
                  command=_submit).pack(pady=12)

    # ── HWID SIFIRLA ──
    def _reset_hwid(self):
        uid = self._selected_id()
        if uid is None:
            return
        name = self.tree.item(str(uid))["values"][0]
        if not messagebox.askyesno("HWID Sıfırla",
                f"'{name}' farklı bilgisayardan giriş yapabilsin mi?"):
            return
        result = api("POST", "/admin/reset_hwid", json={"id": uid})
        if "error" in result:
            messagebox.showerror("Hata", result["error"])
        else:
            messagebox.showinfo("✅", "HWID sıfırlandı.")
            self._refresh()


def main():
    root = tk.Tk()
    AdminApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
