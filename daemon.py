"""
daemon.py
KeyGuard background daemon — monitors all system keystrokes silently.
Scores sliding windows, fires alert popup on anomaly detection.

Can be run standalone or launched from main.py.

Usage: python daemon.py --user gabe4
"""

import argparse
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from collections import deque
import sys

from keystroke_capture import KeystrokeCapture
from feature_extraction import extract_features
from model import KeyGuardModel

WINDOW_SIZE       = 80
SLIDE_EVERY       = 40
CONSECUTIVE_ALERT = 2    # flags in a row before alert popup


class AlertWindow:
    """Popup alert shown when anomaly detected."""

    def __init__(self, score, wpm, window_num, on_dismiss):
        self.root = tk.Tk()
        self.root.title("KeyGuard — Security Alert")
        self.root.configure(bg="#1a0000")
        self.root.geometry("480x280")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.lift()

        mono = tkfont.Font(family="Courier New", size=11)
        big  = tkfont.Font(family="Courier New", size=16, weight="bold")
        sm   = tkfont.Font(family="Courier New", size=10)
        xs   = tkfont.Font(family="Courier New", size=9)

        tk.Label(
            self.root, text="🚨  SECURITY ALERT",
            bg="#1a0000", fg="#ff4444",
            font=tkfont.Font(family="Courier New", size=18, weight="bold")
        ).pack(pady=(28, 4))

        tk.Label(
            self.root,
            text="Unauthorized typing pattern detected.",
            bg="#1a0000", fg="#ff8888", font=mono
        ).pack()

        tk.Frame(self.root, bg="#330000", height=1).pack(fill="x", padx=40, pady=(20, 16))

        tk.Label(
            self.root,
            text=f"Anomaly score:  {score:.3f}   ·   WPM: {wpm:.0f}   ·   Window: {window_num}",
            bg="#1a0000", fg="#664444", font=xs
        ).pack()

        tk.Label(
            self.root,
            text="The current user does not match the enrolled profile.\nSession may be compromised.",
            bg="#1a0000", fg="#884444", font=sm,
            justify="center"
        ).pack(pady=(12, 0))

        btn_frame = tk.Frame(self.root, bg="#1a0000")
        btn_frame.pack(pady=(24, 0))

        tk.Button(
            btn_frame,
            text="  DISMISS  ",
            bg="#333333", fg="#ffffff",
            font=tkfont.Font(family="Courier New", size=10),
            relief="flat", cursor="hand2",
            command=lambda: self._dismiss(on_dismiss, lock=False)
        ).pack(side="left", padx=8)

        tk.Button(
            btn_frame,
            text="  LOCK SESSION  ",
            bg="#ff4444", fg="#ffffff",
            font=tkfont.Font(family="Courier New", size=10, weight="bold"),
            relief="flat", cursor="hand2",
            command=lambda: self._dismiss(on_dismiss, lock=True)
        ).pack(side="left", padx=8)

        self.root.protocol("WM_DELETE_WINDOW", lambda: self._dismiss(on_dismiss, lock=False))

    def _dismiss(self, on_dismiss, lock=False):
        self.root.destroy()
        if lock:
            import os
            if sys.platform == "win32":
                os.system("rundll32.exe user32.dll,LockWorkStation")
        on_dismiss()

    def run(self):
        self.root.mainloop()


class KeyGuardDaemon:
    """
    Background daemon — captures all system keystrokes,
    scores sliding windows, fires alert on anomaly.
    """

    def __init__(self, username: str, status_callback=None):
        self.username        = username
        self.status_callback = status_callback  # optional UI callback
        self.model           = KeyGuardModel(username=username)
        self.model.load()

        self.capture          = KeystrokeCapture()
        self.keystroke_buffer = deque()
        self.new_since_last   = 0
        self.consecutive_flags = 0
        self.window_num       = 0
        self.alert_open       = False
        self.running          = False

        self._thread = None

    def start(self):
        self.running = True
        self.capture.start()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._update_status("Monitoring active — all keystrokes being analyzed.")

    def stop(self):
        self.running = False
        self.capture.stop()

    def _run(self):
        while self.running:
            time.sleep(0.2)
            new_events  = self.capture.flush()
            new_presses = [e for e in new_events if e['event'] == 'press']

            if not new_presses:
                continue

            self.keystroke_buffer.extend(new_events)
            self.new_since_last += len(new_presses)

            # Trim buffer
            press_count = sum(1 for e in self.keystroke_buffer if e['event'] == 'press')
            while press_count > WINDOW_SIZE:
                e = self.keystroke_buffer.popleft()
                if e['event'] == 'press':
                    press_count -= 1

            total = sum(1 for e in self.keystroke_buffer if e['event'] == 'press')

            if self.new_since_last >= SLIDE_EVERY and total >= WINDOW_SIZE:
                features = extract_features(list(self.keystroke_buffer))
                self.new_since_last = 0

                if features is None:
                    continue

                result = self.model.score(features)
                flag   = result['is_anomaly']
                self.window_num += 1

                # Online learning
                self.model.adapt(features, alpha=0.005)

                if flag:
                    self.consecutive_flags += 1
                    self._update_status(
                        f"⚠️  Anomaly detected — window {self.window_num} "
                        f"(score: {result['anomaly_score']:.3f}, "
                        f"consecutive: {self.consecutive_flags})"
                    )
                    if self.consecutive_flags >= CONSECUTIVE_ALERT and not self.alert_open:
                        self.alert_open = True
                        # Auto-lock session immediately
                        self._lock_session()
                        threading.Thread(
                            target=self._show_alert,
                            args=(result['anomaly_score'], features[5], self.window_num),
                            daemon=True
                        ).start()
                else:
                    self.consecutive_flags = 0
                    self._update_status(
                        f"✅ Window {self.window_num} — verified  "
                        f"(score: {result['anomaly_score']:.3f}, "
                        f"WPM: {features[5]:.0f})"
                    )

    def _lock_session(self):
        import os, sys
        self._update_status("🔒 Session locked — unauthorized user detected.")
        if sys.platform == "win32":
            os.system("rundll32.exe user32.dll,LockWorkStation")

    def _show_alert(self, score, wpm, window_num):
        def on_dismiss():
            self.alert_open       = False
            self.consecutive_flags = 0
        AlertWindow(score, wpm, window_num, on_dismiss).run()

    def _update_status(self, msg):
        print(f"[KeyGuard] {msg}")
        if self.status_callback:
            self.status_callback(msg)


# ------------------------------------------------------------------ #
#  Standalone entry point                                             #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    args = parser.parse_args()

    print(f"[KeyGuard] Starting daemon for user '{args.user}'")
    print(f"[KeyGuard] Type anywhere on your computer — monitoring all keystrokes.")
    print(f"[KeyGuard] Press Ctrl+C to stop.\n")

    daemon = KeyGuardDaemon(username=args.user)
    daemon.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.stop()
        print("\n[KeyGuard] Daemon stopped.")
