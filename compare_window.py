"""
compare_window.py - KeyGuard
Side-by-side user comparison with professional dark UI.
"""

import argparse
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from collections import deque
import numpy as np

from keystroke_capture import KeystrokeCapture
from feature_extraction import extract_features, FEATURE_NAMES
from model import KeyGuardModel

WINDOW_SIZE = 80
SLIDE_EVERY = 40

FEATURE_LABELS = ['mean dwell','std dwell','std flight','pause rate','backspace rate','burst WPM','digraph: th','digraph: is','digraph: en']
FEATURE_IDX    = [0, 1, 2, 3, 4, 5, 6, 25, 13]

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
GREEN   = "#2ecc71"
RED     = "#e74c3c"
AMBER   = "#f39c12"


class CompareWindow:
    def __init__(self, username):
        self.username   = username
        self.model      = KeyGuardModel(username=username)
        self.model.load()
        self.capture_a  = KeystrokeCapture()
        self.capture_b  = KeystrokeCapture()
        self.buf_a      = deque()
        self.buf_b      = deque()
        self.new_a      = 0
        self.new_b      = 0
        self.feats_a    = None
        self.feats_b    = None
        self.active     = None
        self.root       = tk.Tk()
        self._build()

    def _f(self, size, weight="normal", family="Segoe UI"):
        return tkfont.Font(family=family, size=size, weight=weight)

    def _build(self):
        self.root.title("KeyGuard — User Comparison")
        self.root.configure(bg=BG)
        self.root.geometry("1100x760")
        self.root.minsize(900, 600)

        # Top bar
        bar = tk.Frame(self.root, bg=BG2, height=44)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        lf = tk.Frame(bar, bg=BG2)
        lf.pack(side="left", padx=18, pady=10)
        tk.Label(lf, text="⬡", bg=BG2, fg=BLUE, font=self._f(12,"bold")).pack(side="left")
        tk.Label(lf, text="  KEYGUARD", bg=BG2, fg=TXT, font=self._f(11,"bold")).pack(side="left")
        tk.Label(lf, text="  /  USER COMPARISON", bg=BG2, fg=TXT3, font=self._f(9)).pack(side="left")
        tk.Frame(self.root, bg=LINE, height=1).pack(fill="x")

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Top: two typing panels ───────────────────────────────── #
        top = tk.Frame(body, bg=BG)
        top.pack(fill="x", pady=(0,16))

        self._typing_panel(top, "left",  self.username.upper(), GREEN, "a").pack(side="left", fill="both", expand=True, padx=(0,8))
        self._typing_panel(top, "right", "FRIEND",              RED,   "b").pack(side="left", fill="both", expand=True, padx=(8,0))

        # ── Feature comparison table ─────────────────────────────── #
        tk.Label(body, text="FEATURE COMPARISON", bg=BG, fg=TXT3,
                 font=self._f(7,"bold")).pack(anchor="w", pady=(0,6))

        table_frame = tk.Frame(body, bg=BG2)
        table_frame.pack(fill="x")
        tk.Frame(body, bg=BG2, width=3, height=3).pack()  # spacer

        # Header
        hdr = tk.Frame(table_frame, bg=BG3, padx=12, pady=6)
        hdr.pack(fill="x")
        for text, width, anchor in [
            ("FEATURE", 22, "w"),
            (self.username.upper(), 12, "e"),
            ("FRIEND", 12, "e"),
            ("DIFFERENCE", 12, "e"),
            ("SEPARATION", 10, "e"),
        ]:
            tk.Label(hdr, text=text, bg=BG3, fg=TXT3,
                     font=self._f(7,"bold","Consolas"),
                     width=width, anchor=anchor).pack(side="left")

        self.row_vars = []
        for i, label in enumerate(FEATURE_LABELS):
            row_bg = BG2 if i % 2 == 0 else BG3
            row = tk.Frame(table_frame, bg=row_bg, padx=12, pady=5)
            row.pack(fill="x")

            tk.Label(row, text=label, bg=row_bg, fg=TXT2,
                     font=self._f(8,"normal","Consolas"),
                     width=22, anchor="w").pack(side="left")

            vars_dict = {}
            for key, width, color in [
                ("val_a", 12, GREEN),
                ("val_b", 12, RED),
                ("diff",  12, TXT3),
                ("flag",  10, TXT3),
            ]:
                v = tk.StringVar(value="—")
                lbl = tk.Label(row, textvariable=v, bg=row_bg,
                               fg=color, font=self._f(9,"normal","Consolas"),
                               width=width, anchor="e")
                lbl.pack(side="left")
                vars_dict[key] = (v, lbl, row_bg)
            self.row_vars.append(vars_dict)

        # ── Score bar ────────────────────────────────────────────── #
        sf = tk.Frame(body, bg=BG)
        sf.pack(fill="x", pady=(12,0))

        left_s  = tk.Frame(sf, bg=BG2)
        left_s.pack(side="left", fill="both", expand=True, padx=(0,8))
        tk.Frame(left_s, bg=GREEN, width=2).pack(side="left", fill="y")
        li = tk.Frame(left_s, bg=BG2, padx=14, pady=10)
        li.pack(fill="both", expand=True)
        tk.Label(li, text=self.username.upper(), bg=BG2, fg=TXT3,
                 font=self._f(7,"bold")).pack(anchor="w")
        self.score_a = tk.StringVar(value="Waiting for data...")
        tk.Label(li, textvariable=self.score_a, bg=BG2, fg=GREEN,
                 font=self._f(11,"bold")).pack(anchor="w")

        right_s = tk.Frame(sf, bg=BG2)
        right_s.pack(side="left", fill="both", expand=True, padx=(8,0))
        tk.Frame(right_s, bg=RED, width=2).pack(side="left", fill="y")
        ri = tk.Frame(right_s, bg=BG2, padx=14, pady=10)
        ri.pack(fill="both", expand=True)
        tk.Label(ri, text="FRIEND", bg=BG2, fg=TXT3,
                 font=self._f(7,"bold")).pack(anchor="w")
        self.score_b = tk.StringVar(value="Waiting for data...")
        tk.Label(ri, textvariable=self.score_b, bg=BG2, fg=RED,
                 font=self._f(11,"bold")).pack(anchor="w")

        # Footer
        tk.Frame(self.root, bg=LINE, height=1).pack(fill="x", side="bottom")
        foot = tk.Frame(self.root, bg=BG2, height=24)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        tk.Label(foot, text="Click a button above to activate that user's typing panel",
                 bg=BG2, fg=TXT3, font=self._f(7,"normal","Consolas")).pack(side="left", padx=14)
        tk.Label(foot, text="● SECURE", bg=BG2, fg=GREEN,
                 font=self._f(7,"normal","Consolas")).pack(side="right", padx=14)

    def _typing_panel(self, parent, side, label, color, who):
        frame = tk.Frame(parent, bg=BG2)

        # Header button
        btn = tk.Frame(frame, bg=color if who=="a" else LINE2, cursor="hand2")
        btn.pack(fill="x")
        tk.Frame(btn, bg=color, width=2).pack(side="left", fill="y")
        bi = tk.Frame(btn, bg=btn.cget("bg"), padx=12, pady=8)
        bi.pack(fill="both", expand=True)
        tk.Label(bi, text=label, bg=bi.cget("bg"),
                 fg=BG if who=="a" else TXT2,
                 font=self._f(9,"bold")).pack(anchor="w")
        sub_v = tk.StringVar(value="Active — type naturally" if who=="a" else "Click to activate")
        tk.Label(bi, textvariable=sub_v, bg=bi.cget("bg"),
                 fg=BG if who=="a" else TXT3,
                 font=self._f(7)).pack(anchor="w")

        if who == "a":
            self.sub_a = sub_v
            self.btn_a = btn
            self.bi_a  = bi
        else:
            self.sub_b = sub_v
            self.btn_b = btn
            self.bi_b  = bi

        def activate(e=None): self._activate(who)
        for w in [btn, bi] + list(bi.winfo_children()):
            try: w.bind("<Button-1>", activate)
            except: pass

        # Text box
        tb_border = tk.Frame(frame, bg=LINE, padx=1, pady=1)
        tb_border.pack(fill="both", expand=True)
        tb = tk.Text(
            tb_border, height=6, wrap="word",
            bg=BG3, fg=TXT,
            insertbackground=color,
            font=self._f(10,"normal","Consolas"),
            relief="flat", bd=0, padx=12, pady=10,
            state="disabled"
        )
        tb.pack(fill="both", expand=True)

        status_v = tk.StringVar(value="—  keystrokes")
        tk.Label(frame, textvariable=status_v, bg=BG2, fg=TXT3,
                 font=self._f(7,"normal","Consolas"), anchor="w").pack(fill="x", padx=6, pady=4)

        if who == "a":
            self.tb_a     = tb
            self.status_a = status_v
        else:
            self.tb_b     = tb
            self.status_b = status_v

        return frame

    def _activate(self, who):
        if self.active == "a": self.capture_a.stop()
        elif self.active == "b": self.capture_b.stop()
        self.active = who

        # Update button styles
        for w, color, is_active in [("a", GREEN, who=="a"), ("b", RED, who=="b")]:
            btn  = self.btn_a  if w=="a" else self.btn_b
            bi   = self.bi_a   if w=="a" else self.bi_b
            sub  = self.sub_a  if w=="a" else self.sub_b
            tb   = self.tb_a   if w=="a" else self.tb_b
            col  = GREEN if w=="a" else RED
            if is_active:
                btn.configure(bg=col)
                bi.configure(bg=col)
                for c in bi.winfo_children():
                    try: c.configure(bg=col, fg=BG)
                    except: pass
                sub.set("Active — type naturally")
                tb.configure(state="normal")
                tb.focus_set()
            else:
                btn.configure(bg=LINE2)
                bi.configure(bg=LINE2)
                for c in bi.winfo_children():
                    try: c.configure(bg=LINE2, fg=TXT3)
                    except: pass
                sub.set("Click to activate")
                tb.configure(state="disabled")

        cap = KeystrokeCapture()
        if who == "a":
            self.capture_a = cap
            self.buf_a.clear(); self.new_a = 0
        else:
            self.capture_b = cap
            self.buf_b.clear(); self.new_b = 0
        cap.start()
        threading.Thread(target=self._collect, args=(who,), daemon=True).start()

    def _collect(self, who):
        cap = self.capture_a if who=="a" else self.capture_b
        buf = self.buf_a     if who=="a" else self.buf_b

        while self.active == who:
            time.sleep(0.2)
            evts = cap.flush()
            prs  = [e for e in evts if e['event']=='press']
            if not prs: continue
            buf.extend(evts)
            if who=="a": self.new_a += len(prs)
            else:        self.new_b += len(prs)

            pc = sum(1 for e in buf if e['event']=='press')
            while pc > WINDOW_SIZE:
                e = buf.popleft()
                if e['event']=='press': pc -= 1

            total = sum(1 for e in buf if e['event']=='press')
            stat  = self.status_a if who=="a" else self.status_b
            self.root.after(0, stat.set, f"{total} / {WINDOW_SIZE}  keystrokes")

            new = self.new_a if who=="a" else self.new_b
            if new >= SLIDE_EVERY and total >= WINDOW_SIZE:
                feats = extract_features(list(buf))
                if who=="a": self.new_a = 0
                else:        self.new_b = 0
                if feats is not None:
                    if who=="a": self.feats_a = feats
                    else:        self.feats_b = feats
                    self.root.after(0, self._update_table)

    def _update_table(self):
        fa = self.feats_a
        fb = self.feats_b

        if fa is not None:
            r = self.model.score(fa)
            flag = r['is_anomaly']
            self.score_a.set(
                f"{'⚠  ANOMALY' if flag else '✓  VERIFIED'}  ·  score: {r['anomaly_score']:.3f}  ·  WPM: {fa[5]:.0f}"
            )

        if fb is not None:
            r = self.model.score(fb)
            flag = r['is_anomaly']
            self.score_b.set(
                f"{'⚠  ANOMALY' if flag else '✓  VERIFIED'}  ·  score: {r['anomaly_score']:.3f}  ·  WPM: {fb[5]:.0f}"
            )

        for i, (label, idx) in enumerate(zip(FEATURE_LABELS, FEATURE_IDX)):
            rv   = self.row_vars[i]
            va   = fa[idx] if fa is not None else None
            vb   = fb[idx] if fb is not None else None

            if va is not None:
                rv["val_a"][0].set(f"{va:.4f}")
            if vb is not None:
                rv["val_b"][0].set(f"{vb:.4f}")
            if va is not None and vb is not None:
                diff  = vb - va
                std   = self.model.enrollment_std[idx]
                zsep  = abs(diff) / max(std, 1e-9)
                color = RED if zsep > 1.5 else (AMBER if zsep > 0.8 else TXT3)
                rv["diff"][0].set(f"{diff:+.4f}")
                rv["diff"][1].configure(fg=color)
                rv["flag"][0].set(f"z={zsep:.1f}")
                rv["flag"][1].configure(fg=color)

    def run(self):
        # Auto-activate user A
        self.root.after(200, lambda: self._activate("a"))
        self.root.mainloop()
        self.capture_a.stop()
        self.capture_b.stop()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--user", required=True)
    a = p.parse_args()
    CompareWindow(a.user).run()
