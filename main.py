"""
main.py — KeyGuard Launcher
CrowdStrike-inspired professional dark UI.
"""

import subprocess
import sys
import os
import tkinter as tk
from tkinter import font as tkfont
from model import KeyGuardModel

PYTHON = sys.executable

BG      = "#0b0c0f"
BG2     = "#13151a"
BG3     = "#1a1d24"
BG4     = "#21242d"
LINE    = "#2a2d38"
LINE2   = "#363a47"
TXT     = "#f0f2f5"
TXT2    = "#9098a9"
TXT3    = "#555e70"
BLUE    = "#4d9fff"
BLUE2   = "#1a6ec5"
GREEN   = "#2ecc71"
RED     = "#e74c3c"
AMBER   = "#f39c12"


class Launcher:
    def __init__(self):
        self.daemon         = None
        self.daemon_running = False
        self.root           = tk.Tk()
        self._build()

    def _f(self, size, weight="normal", family="Segoe UI"):
        return tkfont.Font(family=family, size=size, weight=weight)

    def _build(self):
        self.root.title("KeyGuard")
        self.root.configure(bg=BG)
        self.root.geometry("480x700")
        self.root.resizable(False, False)

        # ── Top bar ─────────────────────────────────────────────── #
        bar = tk.Frame(self.root, bg=BG2, height=44)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        lf = tk.Frame(bar, bg=BG2)
        lf.pack(side="left", padx=18, pady=10)
        tk.Label(lf, text="⬡", bg=BG2, fg=BLUE,
                 font=self._f(12, "bold")).pack(side="left")
        tk.Label(lf, text="  KEYGUARD", bg=BG2, fg=TXT,
                 font=self._f(11, "bold")).pack(side="left")
        tk.Frame(self.root, bg=LINE, height=1).pack(fill="x")

        # ── Body ────────────────────────────────────────────────── #
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # Tagline
        tk.Label(body,
                 text="Continuous authentication\nvia keystroke behavioral biometrics.",
                 bg=BG, fg=TXT2, font=self._f(10), justify="left"
                 ).pack(anchor="w", pady=(0, 20))

        # ── User input ──────────────────────────────────────────── #
        tk.Label(body, text="USER PROFILE", bg=BG, fg=TXT3,
                 font=self._f(7, "bold")).pack(anchor="w", pady=(0, 4))

        last = 'gabe4'
        try:
            with open('.keyguard_last_user') as f:
                last = f.read().strip()
        except:
            pass

        self.user_var = tk.StringVar(value=last)
        ef = tk.Frame(body, bg=LINE, padx=1, pady=1)
        ef.pack(fill="x", pady=(0, 20))
        tk.Entry(ef, textvariable=self.user_var,
                 bg=BG2, fg=TXT, insertbackground=BLUE,
                 font=self._f(11, family="Consolas"),
                 relief="flat", bd=0
                 ).pack(fill="x", ipady=10, padx=12)

        # ── Primary actions ─────────────────────────────────────── #
        tk.Label(body, text="ACTIONS", bg=BG, fg=TXT3,
                 font=self._f(7, "bold")).pack(anchor="w", pady=(0, 6))

        self._btn(body, "Enroll New User",
                  "Learn your typing fingerprint  (~2 min)",
                  BLUE, self._enroll).pack(fill="x", pady=(0, 6))

        self._btn(body, "Start Monitoring",
                  "Live session with real-time anomaly detection",
                  GREEN, self._monitor).pack(fill="x", pady=(0, 6))

        self.daemon_title = tk.StringVar(value="Start Background Daemon")
        self.daemon_sub   = tk.StringVar(value="Silent system-wide monitoring — works across all apps")
        self._btn(body, None, None, TXT3, self._toggle_daemon,
                  title_var=self.daemon_title,
                  sub_var=self.daemon_sub,
                  accent_attr="_daemon_accent"
                  ).pack(fill="x", pady=(0, 20))

        # ── Divider ─────────────────────────────────────────────── #
        tk.Frame(body, bg=LINE, height=1).pack(fill="x", pady=(0, 16))

        # ── Tools ───────────────────────────────────────────────── #
        tk.Label(body, text="ANALYSIS TOOLS", bg=BG, fg=TXT3,
                 font=self._f(7, "bold")).pack(anchor="w", pady=(0, 8))

        tools = [
            ("Compare Users",      "Side-by-side feature comparison",        self._compare),
            ("Visualize Clusters", "PCA projection of typing fingerprints",   self._visualize),
            ("Optimize Model",     "Feature separation analysis",             self._optimize),
            ("Enroll Friend",      "Capture a second user's typing data",     self._enroll_friend),
        ]
        for title, sub, cmd in tools:
            self._tool_row(body, title, sub, cmd).pack(fill="x", pady=(0, 4))

        # ── Divider ─────────────────────────────────────────────── #
        tk.Frame(body, bg=LINE, height=1).pack(fill="x", pady=(12, 10))

        # ── Status ──────────────────────────────────────────────── #
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(body, textvariable=self.status_var,
                 bg=BG, fg=TXT3, font=self._f(8, family="Consolas"),
                 wraplength=420, justify="left", anchor="w"
                 ).pack(fill="x")

        # ── Footer ──────────────────────────────────────────────── #
        tk.Frame(self.root, bg=LINE, height=1).pack(fill="x", side="bottom")
        foot = tk.Frame(self.root, bg=BG2, height=24)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        tk.Label(foot,
                 text="Your typing fingerprint never leaves this device.",
                 bg=BG2, fg=TXT3, font=self._f(7, family="Consolas")
                 ).pack(side="left", padx=14)
        tk.Label(foot, text="● SECURE", bg=BG2, fg=GREEN,
                 font=self._f(7, family="Consolas")).pack(side="right", padx=14)

    # ── Button builders ──────────────────────────────────────────── #
    def _btn(self, parent, title, subtitle, color, cmd,
             title_var=None, sub_var=None, accent_attr=None):
        frame = tk.Frame(parent, bg=BG2, cursor="hand2")

        accent = tk.Frame(frame, bg=color, width=2)
        accent.pack(side="left", fill="y")
        if accent_attr:
            setattr(self, accent_attr, accent)

        inner = tk.Frame(frame, bg=BG2, padx=14, pady=12)
        inner.pack(fill="both", expand=True)

        if title_var:
            tk.Label(inner, textvariable=title_var, bg=BG2, fg=TXT,
                     font=self._f(10, "bold"), anchor="w").pack(anchor="w")
        else:
            tk.Label(inner, text=title, bg=BG2, fg=TXT,
                     font=self._f(10, "bold"), anchor="w").pack(anchor="w")

        if sub_var:
            tk.Label(inner, textvariable=sub_var, bg=BG2, fg=TXT3,
                     font=self._f(8), anchor="w").pack(anchor="w", pady=(2,0))
        else:
            tk.Label(inner, text=subtitle, bg=BG2, fg=TXT3,
                     font=self._f(8), anchor="w").pack(anchor="w", pady=(2,0))

        def on_click(e=None): cmd()
        def on_enter(e=None):
            frame.configure(bg=BG3)
            inner.configure(bg=BG3)
            for w in inner.winfo_children():
                try: w.configure(bg=BG3)
                except: pass
        def on_leave(e=None):
            frame.configure(bg=BG2)
            inner.configure(bg=BG2)
            for w in inner.winfo_children():
                try: w.configure(bg=BG2)
                except: pass

        for w in [frame, inner] + list(inner.winfo_children()):
            try:
                w.bind("<Button-1>", on_click)
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)
            except: pass

        return frame

    def _tool_row(self, parent, title, subtitle, cmd):
        frame = tk.Frame(parent, bg=BG3, cursor="hand2")

        inner = tk.Frame(frame, bg=BG3, padx=14, pady=8)
        inner.pack(fill="x", expand=True)

        top = tk.Frame(inner, bg=BG3)
        top.pack(fill="x")
        tk.Label(top, text=title, bg=BG3, fg=TXT2,
                 font=self._f(9, "bold"), anchor="w").pack(side="left")
        tk.Label(top, text="→", bg=BG3, fg=TXT3,
                 font=self._f(9)).pack(side="right")
        tk.Label(inner, text=subtitle, bg=BG3, fg=TXT3,
                 font=self._f(8), anchor="w").pack(anchor="w")

        def on_click(e=None): cmd()
        def on_enter(e=None):
            frame.configure(bg=BG4)
            inner.configure(bg=BG4)
            for w in inner.winfo_children() + top.winfo_children():
                try: w.configure(bg=BG4)
                except: pass
        def on_leave(e=None):
            frame.configure(bg=BG3)
            inner.configure(bg=BG3)
            for w in inner.winfo_children() + top.winfo_children():
                try: w.configure(bg=BG3)
                except: pass

        for w in [frame, inner, top] + list(inner.winfo_children()) + list(top.winfo_children()):
            try:
                w.bind("<Button-1>", on_click)
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)
            except: pass

        return frame

    # ── Helpers ─────────────────────────────────────────────────── #
    def _get_user(self):
        u = self.user_var.get().strip()
        if not u:
            self.status_var.set("Enter a username first.")
            return None
        try:
            with open('.keyguard_last_user', 'w') as f:
                f.write(u)
        except: pass
        return u

    def _set_status(self, msg):
        self.status_var.set(msg)

    # ── Actions ─────────────────────────────────────────────────── #
    def _enroll(self):
        u = self._get_user()
        if u:
            self._set_status(f"Opening enrollment for '{u}'...")
            subprocess.Popen([PYTHON, "typing_window.py", "--mode", "enroll", "--user", u])

    def _monitor(self):
        u = self._get_user()
        if not u: return
        if not KeyGuardModel(username=u).model_exists():
            self._set_status(f"No model for '{u}'. Enroll first.")
            return
        self._set_status(f"Opening monitor for '{u}'...")
        subprocess.Popen([PYTHON, "typing_window.py", "--mode", "exam", "--user", u])

    def _toggle_daemon(self):
        if self.daemon_running:
            if self.daemon:
                self.daemon.stop()
                self.daemon = None
            self.daemon_running = False
            self.daemon_title.set("Start Background Daemon")
            self.daemon_sub.set("Silent system-wide monitoring — works across all apps")
            if hasattr(self, '_daemon_accent'):
                self._daemon_accent.configure(bg=TXT3)
            self._set_status("Daemon stopped.")
        else:
            u = self._get_user()
            if not u: return
            if not KeyGuardModel(username=u).model_exists():
                self._set_status(f"No model for '{u}'. Enroll first.")
                return
            from daemon import KeyGuardDaemon
            self.daemon = KeyGuardDaemon(
                username=u,
                status_callback=lambda msg: self.root.after(0, self._set_status, msg)
            )
            self.daemon.start()
            self.daemon_running = True
            self.daemon_title.set("Stop Background Daemon")
            self.daemon_sub.set(f"Monitoring '{u}' — click to stop")
            if hasattr(self, '_daemon_accent'):
                self._daemon_accent.configure(bg=GREEN)
            self._set_status(f"Daemon active for '{u}'. Type anywhere on your computer.")

    def _compare(self):
        u = self._get_user()
        if u:
            subprocess.Popen([PYTHON, "compare_window.py", "--user", u])

    def _visualize(self):
        u = self._get_user()
        if u:
            subprocess.Popen([PYTHON, "visualize_embeddings.py", "--user", u])

    def _optimize(self):
        u = self._get_user()
        if u:
            subprocess.Popen([PYTHON, "optimize.py", "--user", u])

    def _enroll_friend(self):
        subprocess.Popen([PYTHON, "enroll_friend.py"])

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    Launcher().run()
