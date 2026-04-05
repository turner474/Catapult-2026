"""
typing_window.py - KeyGuard
CrowdStrike-inspired professional dark security UI.
"""

import argparse
import random
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from collections import deque

from keystroke_capture import KeystrokeCapture
from feature_extraction import extract_features, FEATURE_NAMES, N_AGG
from model import KeyGuardModel

WINDOW_SIZE = 80
SLIDE_EVERY = 40
TARGET_WIN  = 16

# ── Palette (CrowdStrike-inspired) ──────────────────────────────── #
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
GREEN2  = "#1a7a43"
RED     = "#e74c3c"
RED2    = "#8b1a14"
AMBER   = "#f39c12"
CYAN    = "#1abc9c"

PROMPTS = [
    "Type naturally — stream of consciousness, anything at all.",
    "Talk about your day, ideas, or just type freely.",
]


class TypingWindow:
    def __init__(self, mode, username):
        self.mode          = mode
        self.username      = username
        self.capture       = KeystrokeCapture()
        self.score_history = []
        self.flag_history  = []
        self.window_num    = 0
        self.root          = tk.Tk()
        self._fs           = False
        self._build()

    # ── fonts ────────────────────────────────────────────────────── #
    def _f(self, size, weight="normal", family="Segoe UI"):
        return tkfont.Font(family=family, size=size, weight=weight)

    # ── build ────────────────────────────────────────────────────── #
    def _build(self):
        self.root.title("KeyGuard")
        self.root.configure(bg=BG)
        self.root.geometry("1280x820")
        self.root.minsize(960, 640)
        self.root.bind("<F11>", lambda e: self._toggle_fs())
        self.root.bind("<Escape>", lambda e: self._set_fs(False))

        self._topbar()
        tk.Frame(self.root, bg=LINE, height=1).pack(fill="x")

        if self.mode == "enroll":
            self._enroll_body()
        else:
            self._exam_body()

        self._footer()

    def _topbar(self):
        bar = tk.Frame(self.root, bg=BG2, height=44)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Logo
        lf = tk.Frame(bar, bg=BG2)
        lf.pack(side="left", padx=18, pady=10)
        tk.Label(lf, text="⬡", bg=BG2, fg=BLUE,
                 font=self._f(12, "bold")).pack(side="left")
        tk.Label(lf, text="  KEYGUARD", bg=BG2, fg=TXT,
                 font=self._f(11, "bold")).pack(side="left")
        tk.Label(lf, text="  /  " + ("ENROLLMENT" if self.mode=="enroll" else "CONTINUOUS MONITORING"),
                 bg=BG2, fg=TXT3, font=self._f(9)).pack(side="left")

        # Right
        rf = tk.Frame(bar, bg=BG2)
        rf.pack(side="right", padx=18)
        tk.Label(rf, text="F11", bg=BG2, fg=TXT3,
                 font=self._f(8, family="Consolas")).pack(side="right", padx=(8,0))
        tk.Label(rf, text="●", bg=BG2, fg=BLUE,
                 font=self._f(8)).pack(side="right")
        tk.Label(rf, text=self.username, bg=BG2, fg=TXT2,
                 font=self._f(9)).pack(side="right", padx=(0,4))

    def _footer(self):
        tk.Frame(self.root, bg=LINE, height=1).pack(fill="x", side="bottom")
        bar = tk.Frame(self.root, bg=BG2, height=24)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.footer_var = tk.StringVar(
            value=f"System Active  ·  Sensor Online  ·  Profile: {self.username}"
        )
        tk.Label(bar, textvariable=self.footer_var, bg=BG2, fg=TXT3,
                 font=self._f(8, family="Consolas")).pack(side="left", padx=14)
        tk.Label(bar, text="● LIVE", bg=BG2, fg=GREEN,
                 font=self._f(8, family="Consolas")).pack(side="right", padx=14)

    # ── fullscreen ───────────────────────────────────────────────── #
    def _toggle_fs(self):
        self._fs = not self._fs
        self.root.attributes("-fullscreen", self._fs)

    def _set_fs(self, val):
        self._fs = val
        self.root.attributes("-fullscreen", val)

    # ── enrollment body ──────────────────────────────────────────── #
    def _enroll_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=20)

        # Header card
        hdr = tk.Frame(body, bg=BG2)
        hdr.pack(fill="x", pady=(0,16))
        tk.Frame(hdr, bg=BLUE, width=2).pack(side="left", fill="y")
        hi = tk.Frame(hdr, bg=BG2, padx=18, pady=14)
        hi.pack(fill="both", expand=True)

        tk.Label(hi, text="ENROLLMENT", bg=BG2, fg=TXT3,
                 font=self._f(8, "bold")).pack(anchor="w")
        tk.Label(hi, text="Learning your typing fingerprint",
                 bg=BG2, fg=TXT, font=self._f(14, "bold")).pack(anchor="w", pady=(4,0))

        self.status_var = tk.StringVar(value="Type naturally in the box below. Keep going until complete.")
        tk.Label(hi, textvariable=self.status_var, bg=BG2, fg=TXT2,
                 font=self._f(9)).pack(anchor="w", pady=(6,0))

        # Progress row
        pr = tk.Frame(hi, bg=BG2)
        pr.pack(fill="x", pady=(14,0))
        tk.Label(pr, text="PROGRESS", bg=BG2, fg=TXT3,
                 font=self._f(7, "bold")).pack(side="left")
        self.prog_lbl = tk.StringVar(value="0 / 16 windows")
        tk.Label(pr, textvariable=self.prog_lbl, bg=BG2, fg=TXT3,
                 font=self._f(7, family="Consolas")).pack(side="right")

        self.prog_cv = tk.Canvas(hi, height=3, bg=BG4, highlightthickness=0)
        self.prog_cv.pack(fill="x", pady=(4,0))
        self.prog_cv.bind("<Configure>", lambda e: self._draw_prog(0))

        # Input
        tk.Label(body, text="INPUT", bg=BG, fg=TXT3,
                 font=self._f(8, "bold"), anchor="w").pack(fill="x", pady=(0,4))

        tb = tk.Frame(body, bg=LINE, padx=1, pady=1)
        tb.pack(fill="both", expand=True)
        self.text_box = tk.Text(
            tb, wrap="word", bg=BG2, fg=TXT,
            insertbackground=BLUE,
            font=self._f(11, family="Consolas"),
            relief="flat", bd=0, padx=16, pady=14,
            selectbackground=BLUE2,
        )
        self.text_box.pack(fill="both", expand=True)
        self.text_box.focus_set()

        tk.Label(body, text=random.choice(PROMPTS), bg=BG, fg=TXT3,
                 font=self._f(8), anchor="w").pack(fill="x", pady=(6,0))

    def _draw_prog(self, current):
        c = self.prog_cv
        c.delete("all")
        W = c.winfo_width()
        if W < 2: return
        c.create_rectangle(0, 0, W, 3, fill=BG4, outline="")
        filled = int((current / TARGET_WIN) * W)
        if filled > 0:
            c.create_rectangle(0, 0, filled, 3, fill=BLUE, outline="")

    # ── exam body ────────────────────────────────────────────────── #
    def _exam_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        # Left panel — 300px fixed
        self.left = tk.Frame(body, bg=BG, width=300)
        self.left.pack(side="left", fill="y")
        self.left.pack_propagate(False)
        tk.Frame(body, bg=LINE, width=1).pack(side="left", fill="y")

        # Right panel
        self.right = tk.Frame(body, bg=BG)
        self.right.pack(side="left", fill="both", expand=True)

        self._exam_left()
        self._exam_right()

    def _exam_left(self):
        p = self.left
        pad = dict(padx=20, pady=0)

        # ── Status block ─────────────────────────────────────────── #
        sb = tk.Frame(p, bg=BG2)
        sb.pack(fill="x")
        tk.Frame(sb, bg=BLUE, width=2).pack(side="left", fill="y")
        si = tk.Frame(sb, bg=BG2, padx=16, pady=20)
        si.pack(fill="both", expand=True)

        dot_row = tk.Frame(si, bg=BG2)
        dot_row.pack(anchor="w", fill="x")
        self.s_dot = tk.Label(dot_row, text="●", bg=BG2, fg=TXT3,
                               font=self._f(9))
        self.s_dot.pack(side="left")
        self.s_badge = tk.Label(dot_row, text="INITIALIZING", bg=BG2, fg=TXT3,
                                 font=self._f(7, "bold", "Consolas"))
        self.s_badge.pack(side="left", padx=(6,0))

        self.s_title = tk.Label(si, text="—", bg=BG2, fg=TXT,
                                 font=self._f(18, "bold"), anchor="w")
        self.s_title.pack(anchor="w", pady=(8,2))

        self.s_sub = tk.Label(si, text="Collecting keystroke data...",
                               bg=BG2, fg=TXT2, font=self._f(9),
                               wraplength=240, justify="left", anchor="w")
        self.s_sub.pack(anchor="w")

        tk.Frame(p, bg=LINE, height=1).pack(fill="x")

        # ── Metrics ──────────────────────────────────────────────── #
        mf = tk.Frame(p, bg=BG)
        mf.pack(fill="x")

        for label, attr in [("WINDOWS", "m_win"), ("WPM", "m_wpm"), ("ANOMALY SCORE", "m_score")]:
            row = tk.Frame(mf, bg=BG, padx=20, pady=14)
            row.pack(fill="x")
            tk.Label(row, text=label, bg=BG, fg=TXT3,
                     font=self._f(7, "bold")).pack(anchor="w")
            v = tk.StringVar(value="—")
            tk.Label(row, textvariable=v, bg=BG, fg=TXT,
                     font=self._f(20, "bold", "Consolas")).pack(anchor="w", pady=(2,0))
            setattr(self, attr, v)
            tk.Frame(mf, bg=LINE, height=1).pack(fill="x", padx=20)

        # ── Detectors ────────────────────────────────────────────── #
        df = tk.Frame(p, bg=BG, padx=20, pady=14)
        df.pack(fill="x")
        tk.Label(df, text="DETECTORS", bg=BG, fg=TXT3,
                 font=self._f(7, "bold")).pack(anchor="w", pady=(0,10))

        self.det_vars = {}
        for name, desc in [("Z-SCORE","Statistical Anomaly"),
                            ("IFOREST","Isolation Forest ML"),
                            ("SVM","One-Class SVM")]:
            row = tk.Frame(df, bg=BG3, pady=0)
            row.pack(fill="x", pady=(0,4))
            tk.Frame(row, bg=LINE2, width=2).pack(side="left", fill="y")
            ri = tk.Frame(row, bg=BG3, padx=10, pady=8)
            ri.pack(fill="both", expand=True)
            top = tk.Frame(ri, bg=BG3)
            top.pack(fill="x")
            tk.Label(top, text=name, bg=BG3, fg=TXT2,
                     font=self._f(8, "bold", "Consolas")).pack(side="left")
            v = tk.StringVar(value="—")
            lbl = tk.Label(top, textvariable=v, bg=BG3, fg=TXT3,
                           font=self._f(9, "bold", "Consolas"))
            lbl.pack(side="right")
            tk.Label(ri, text=desc, bg=BG3, fg=TXT3,
                     font=self._f(7)).pack(anchor="w")
            self.det_vars[name] = (v, lbl, row)

        tk.Frame(p, bg=LINE, height=1).pack(fill="x")

        # ── Activity log ─────────────────────────────────────────── #
        lf = tk.Frame(p, bg=BG, padx=20, pady=10)
        lf.pack(fill="both", expand=True)
        tk.Label(lf, text="ACTIVITY LOG", bg=BG, fg=TXT3,
                 font=self._f(7, "bold")).pack(anchor="w", pady=(0,6))
        lb = tk.Frame(lf, bg=LINE, padx=1, pady=1)
        lb.pack(fill="both", expand=True)
        self.log_box = tk.Text(
            lb, wrap="none", bg=BG2, fg=TXT3,
            font=self._f(8, family="Consolas"),
            relief="flat", bd=0, padx=8, pady=6, state="disabled"
        )
        self.log_box.pack(fill="both", expand=True)

    def _exam_right(self):
        p = self.right
        pad = 20

        # ── Graph ────────────────────────────────────────────────── #
        gh = tk.Frame(p, bg=BG, padx=pad, pady=14)
        gh.pack(fill="x")

        gl = tk.Frame(gh, bg=BG)
        gl.pack(fill="x")
        tk.Label(gl, text="ANOMALY SCORE", bg=BG, fg=TXT3,
                 font=self._f(7, "bold")).pack(side="left")
        tk.Label(gl, text="LIVE  ●", bg=BG, fg=GREEN,
                 font=self._f(7, "bold")).pack(side="right")

        gcb = tk.Frame(p, bg=LINE, padx=1, pady=1)
        gcb.pack(fill="x", padx=pad)
        self.graph_cv = tk.Canvas(gcb, height=220, bg=BG2, highlightthickness=0)
        self.graph_cv.pack(fill="x")
        self.graph_cv.bind("<Configure>", lambda e: self._draw_graph())

        # ── Input ────────────────────────────────────────────────── #
        ih = tk.Frame(p, bg=BG, padx=pad, pady=14)
        ih.pack(fill="x")
        tk.Label(ih, text="KEYBOARD INPUT", bg=BG, fg=TXT3,
                 font=self._f(7, "bold")).pack(side="left")
        tk.Label(ih, text="pynput capture active", bg=BG, fg=TXT3,
                 font=self._f(7, family="Consolas")).pack(side="right")

        tb = tk.Frame(p, bg=LINE, padx=1, pady=1)
        tb.pack(fill="both", expand=True, padx=pad, pady=(0, pad))
        self.text_box = tk.Text(
            tb, wrap="word", bg=BG2, fg=TXT,
            insertbackground=BLUE,
            font=self._f(11, family="Consolas"),
            relief="flat", bd=0, padx=16, pady=14,
            selectbackground=BLUE2,
        )
        self.text_box.pack(fill="both", expand=True)
        self.text_box.focus_set()

        # Placeholder
        ph = "Type here to begin authentication monitoring..."
        self.text_box.insert("1.0", ph)
        self.text_box.configure(fg=TXT3)
        self.text_box.bind("<FocusIn>", lambda e: self._clear_ph(ph))

        self.status_var = tk.StringVar(value="")

    def _clear_ph(self, ph):
        if self.text_box.get("1.0", "end-1c") == ph:
            self.text_box.delete("1.0", "end")
            self.text_box.configure(fg=TXT)

    # ── graph ────────────────────────────────────────────────────── #
    def _draw_graph(self):
        c = self.graph_cv
        c.delete("all")
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 4 or H < 4: return

        L, R, T, B = 46, 12, 12, 28
        gW = W - L - R
        gH = H - T - B

        # Grid
        for i, v in enumerate([0.0, 0.25, 0.5, 0.75, 1.0]):
            y = T + gH * (1 - v)
            c.create_line(L, y, W-R, y, fill=BG4, width=1)
            c.create_text(L-4, y, text=f"{v:.2f}", fill=TXT3,
                         font=self._f(7, family="Consolas"), anchor="e")

        # Axes
        c.create_line(L, T, L, T+gH, fill=LINE2, width=1)
        c.create_line(L, T+gH, W-R, T+gH, fill=LINE2, width=1)

        # Threshold
        ty = T + gH * 0.5
        c.create_line(L, ty, W-R, ty, fill=RED, dash=(4,3), width=1)
        c.create_text(W-R-4, ty-7, text="threshold 0.50",
                      fill=RED, font=self._f(7, family="Consolas"), anchor="e")

        if not self.score_history:
            c.create_text(W//2, H//2, text="Awaiting data...",
                          fill=TXT3, font=self._f(9))
            return

        scores = self.score_history[-80:]
        n = len(scores)
        if n < 2: return

        def xy(i, s):
            x = L + (i / max(n-1,1)) * gW
            y = T + gH * (1 - min(max(s,0),1))
            return x, y

        # Area fill
        pts = []
        for i,s in enumerate(scores):
            pts.extend(xy(i,s))
        pts += [xy(n-1,0)[0], T+gH, L, T+gH]
        last_f = self.flag_history[-1] if self.flag_history else False
        c.create_polygon(pts, fill="#1a0a08" if last_f else "#081a0f", outline="")

        # Line — color segments by flag
        for i in range(n-1):
            x1,y1 = xy(i, scores[i])
            x2,y2 = xy(i+1, scores[i+1])
            idx = len(self.flag_history)-n+i
            f = self.flag_history[idx] if 0<=idx<len(self.flag_history) else False
            c.create_line(x1,y1,x2,y2, fill=RED if f else GREEN, width=1.5, smooth=True)

        # Dot
        lx,ly = xy(n-1, scores[-1])
        dc = RED if last_f else GREEN
        c.create_oval(lx-3,ly-3,lx+3,ly+3, fill=dc, outline="")
        c.create_text(lx+6, ly, text=f"{scores[-1]:.3f}",
                      fill=dc, font=self._f(8, family="Consolas"), anchor="w")

        # X label
        c.create_text(W//2, H-6, text=f"last {n} windows",
                      fill=TXT3, font=self._f(7))

    # ── run ──────────────────────────────────────────────────────── #
    def run(self):
        self.capture.start()
        t = self._enroll_loop if self.mode == "enroll" else self._exam_loop
        threading.Thread(target=t, daemon=True).start()
        self.root.mainloop()
        self.capture.stop()

    # ── enrollment loop ──────────────────────────────────────────── #
    def _enroll_loop(self):
        wins, buf, new = [], deque(), 0
        self._set_status("Type naturally — the system is building your profile.")

        while len(wins) < TARGET_WIN:
            time.sleep(0.2)
            evts = self.capture.flush()
            prs  = [e for e in evts if e['event']=='press']
            if not prs: continue
            buf.extend(evts); new += len(prs)
            pc = sum(1 for e in buf if e['event']=='press')
            while pc > WINDOW_SIZE:
                e = buf.popleft()
                if e['event']=='press': pc -= 1
            tot = sum(1 for e in buf if e['event']=='press')
            if new >= SLIDE_EVERY and tot >= WINDOW_SIZE:
                f = extract_features(list(buf)); new = 0
                if f is not None:
                    wins.append(f)
                    n = len(wins)
                    self.root.after(0, self._draw_prog, n)
                    self.root.after(0, self.prog_lbl.set, f"{n} / {TARGET_WIN} windows")
                    self._set_status(f"Window {n}/{TARGET_WIN}  ·  WPM: {f[5]:.0f}  ·  Keep typing!")

        self._set_status("Training model...")
        m = KeyGuardModel(username=self.username)
        m.train(wins); m.save()
        self.root.after(0, self._draw_prog, TARGET_WIN)
        self._set_status("✓  Complete — model saved. You can close this window.")
        self.root.after(0, self.footer_var.set, f"Enrollment complete  ·  {TARGET_WIN} windows  ·  Model saved")

    # ── exam loop ────────────────────────────────────────────────── #
    def _exam_loop(self):
        model = KeyGuardModel(username=self.username)
        model.load()
        consec, buf, new = 0, deque(), 0
        self.root.after(0, self.s_title.configure, {"text": "Monitoring"})
        self.root.after(0, self.s_dot.configure, {"fg": BLUE})

        while True:
            time.sleep(0.2)
            evts = self.capture.flush()
            prs  = [e for e in evts if e['event']=='press']
            if not prs: continue
            buf.extend(evts); new += len(prs)
            pc = sum(1 for e in buf if e['event']=='press')
            while pc > WINDOW_SIZE:
                e = buf.popleft()
                if e['event']=='press': pc -= 1
            tot = sum(1 for e in buf if e['event']=='press')
            if new >= SLIDE_EVERY and tot >= WINDOW_SIZE:
                feats = extract_features(list(buf)); new = 0
                if feats is None: continue
                result = model.score(feats)
                flag   = result['is_anomaly']
                self.window_num += 1
                consec = consec+1 if flag else 0
                model.adapt(feats, alpha=0.005)
                self.score_history.append(result['anomaly_score'])
                self.flag_history.append(flag)
                self.root.after(0, self._update, result, feats[5], consec)

    # ── update display ───────────────────────────────────────────── #
    def _update(self, result, wpm, consec):
        flag  = result['is_anomaly']
        score = result['anomaly_score']

        # Status
        if consec >= 2:
            self.s_dot.configure(fg=RED)
            self.s_badge.configure(text="ALERT", fg=RED)
            self.s_title.configure(text="Unauthorized", fg=RED)
            self.s_sub.configure(text="Typing pattern does not match enrolled profile. Recommend session lock.")
            self.root.configure(bg="#120808")
            self.left.configure(bg="#120808")
            self.right.configure(bg="#120808")
            self.footer_var.set(f"⚠  UNAUTHORIZED USER  ·  {consec} consecutive anomalous windows  ·  W{self.window_num:02d}")
        elif flag:
            self.s_dot.configure(fg=AMBER)
            self.s_badge.configure(text="ANOMALY", fg=AMBER)
            self.s_title.configure(text="Anomaly Detected", fg=AMBER)
            self.s_sub.configure(text=f"Unusual pattern detected. Monitoring closely. ({consec} flag)")
            self.root.configure(bg=BG)
            self.left.configure(bg=BG)
            self.right.configure(bg=BG)
            self.footer_var.set(f"Anomaly  ·  Score: {score:.3f}  ·  Window {self.window_num:02d}")
        else:
            self.s_dot.configure(fg=GREEN)
            self.s_badge.configure(text="VERIFIED", fg=GREEN)
            self.s_title.configure(text="User Verified", fg=TXT)
            self.s_sub.configure(text="Typing pattern matches enrolled profile.")
            self.root.configure(bg=BG)
            self.left.configure(bg=BG)
            self.right.configure(bg=BG)
            self.footer_var.set(f"System Active  ·  Sensor Online  ·  Profile: {self.username}  ·  W{self.window_num:02d}")

        # Metrics
        self.m_win.set(str(self.window_num))
        self.m_wpm.set(f"{wpm:.0f}")
        self.m_score.set(f"{score:.3f}")

        # Detectors
        for name, flagged in [("Z-SCORE", result['z_flag']),
                               ("IFOREST", result['if_flag']),
                               ("SVM",     result['svm_flag'])]:
            v, lbl, row = self.det_vars[name]
            v.set("FLAGGED" if flagged else "CLEAR")
            lbl.configure(fg=RED if flagged else GREEN)
            row.configure(bg="#1f0a0a" if flagged else BG3)

        # Graph
        self._draw_graph()

        # Log
        line = (f" W{self.window_num:02d}  {'ANOMALY' if flag else 'CLEAR  '}"
                f"  {score:.3f}  {wpm:>4.0f}wpm"
                f"  z:{'F' if result['z_flag'] else '·'}"
                f" if:{'F' if result['if_flag'] else '·'}"
                f" svm:{'F' if result['svm_flag'] else '·'}\n")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line)
        self.log_box.see("end")
        last = int(self.log_box.index("end-1l").split(".")[0]) - 1
        tag  = f"w{self.window_num}"
        self.log_box.tag_add(tag, f"{last}.0", f"{last}.end")
        self.log_box.tag_configure(tag, foreground=RED if flag else TXT3)
        self.log_box.configure(state="disabled")

    def _set_status(self, msg):
        self.root.after(0, self.status_var.set, msg)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["enroll","exam"], required=True)
    p.add_argument("--user", required=True)
    a = p.parse_args()
    TypingWindow(a.mode, a.user).run()
