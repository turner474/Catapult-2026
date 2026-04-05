"""
enroll_friend.py
Friend enrollment with UI — shows a text box so they can see what they're typing.
Saves raw events + feature vectors for analysis.

Usage: python enroll_friend.py
"""

import time
import pickle
import threading
import tkinter as tk
from tkinter import font as tkfont
from collections import deque
from keystroke_capture import KeystrokeCapture
from feature_extraction import extract_features

WINDOW_SIZE = 80
SLIDE_EVERY = 40
TARGET_WIN  = 20
OUTPUT_FILE = "friend_features.pkl"


class FriendEnrollWindow:
    def __init__(self):
        self.capture         = KeystrokeCapture()
        self.keystroke_buffer = deque()
        self.feature_windows = []
        self.all_raw_events  = []
        self.new_since_last  = 0
        self.name            = ""
        self.root            = tk.Tk()
        self._build_ui()

    def _build_ui(self):
        self.root.title("KeyGuard — Friend Enrollment")
        self.root.configure(bg="#0f0f0f")
        self.root.geometry("900x580")
        self.root.resizable(False, False)

        mono = tkfont.Font(family="Courier New", size=12)
        big  = tkfont.Font(family="Courier New", size=15, weight="bold")
        sm   = tkfont.Font(family="Courier New", size=10)

        tk.Label(
            self.root, text="⌨  K E Y G U A R D",
            bg="#0f0f0f", fg="#00ff99",
            font=tkfont.Font(family="Courier New", size=16, weight="bold")
        ).pack(pady=(16, 0))

        tk.Label(
            self.root, text="FRIEND ENROLLMENT",
            bg="#0f0f0f", fg="#555555", font=sm
        ).pack(pady=(2, 10))

        # Name entry
        name_frame = tk.Frame(self.root, bg="#0f0f0f")
        name_frame.pack(padx=40, fill="x", pady=(0, 10))
        tk.Label(
            name_frame, text="Your name:",
            bg="#0f0f0f", fg="#444444", font=sm
        ).pack(side="left")
        self.name_var = tk.StringVar()
        name_entry = tk.Entry(
            name_frame, textvariable=self.name_var,
            bg="#111111", fg="#ffffff",
            insertbackground="#00ff99",
            font=mono, relief="flat", bd=0,
            width=20
        )
        name_entry.pack(side="left", padx=(8, 0))
        name_entry.focus_set()

        tk.Button(
            name_frame,
            text="  START  ",
            bg="#00ff99", fg="#000000",
            font=tkfont.Font(family="Courier New", size=10, weight="bold"),
            relief="flat", cursor="hand2",
            command=self._start
        ).pack(side="left", padx=(16, 0))

        # Prompt
        tk.Label(
            self.root,
            text="Type anything naturally — talk about your day, stream of consciousness...",
            bg="#0f0f0f", fg="#333333", font=sm
        ).pack(padx=40, anchor="w")

        # Typing box
        typing_frame = tk.Frame(self.root, bg="#0f0f0f")
        typing_frame.pack(padx=40, fill="x", pady=(4, 0))
        self.text_box = tk.Text(
            typing_frame,
            height=10, wrap="word",
            bg="#111111", fg="#ffffff",
            insertbackground="#00ff99",
            font=mono, relief="flat", bd=0,
            padx=12, pady=10,
            state="disabled",
        )
        self.text_box.pack(fill="x")

        # Status
        self.status_var = tk.StringVar(value="Enter your name and click START.")
        tk.Label(
            self.root, textvariable=self.status_var,
            bg="#0f0f0f", fg="#00ff99", font=sm
        ).pack(pady=(10, 0))

        # Progress bar
        self.progress_canvas = tk.Canvas(
            self.root, height=8, bg="#0f0f0f",
            highlightthickness=0, width=820
        )
        self.progress_canvas.pack(pady=(6, 0))
        self._draw_progress(0)

    def _draw_progress(self, current):
        c = self.progress_canvas
        c.delete("all")
        filled = int((current / TARGET_WIN) * 820)
        c.create_rectangle(0, 0, 820, 8, fill="#1a1a1a", outline="")
        c.create_rectangle(0, 0, filled, 8, fill="#00ff99", outline="")
        self.root.update_idletasks()

    def _start(self):
        self.name = self.name_var.get().strip() or "friend"
        self.text_box.configure(state="normal")
        self.text_box.focus_set()
        self.status_var.set(f"Hi {self.name}! Type freely — keep going until the bar fills.")
        self.capture.start()
        threading.Thread(target=self._capture_loop, daemon=True).start()

    def _capture_loop(self):
        while len(self.feature_windows) < TARGET_WIN:
            time.sleep(0.2)
            new_events  = self.capture.flush()
            new_presses = [e for e in new_events if e['event'] == 'press']

            if not new_presses:
                continue

            self.all_raw_events.extend(new_events)
            self.keystroke_buffer.extend(new_events)
            self.new_since_last += len(new_presses)

            press_count = sum(1 for e in self.keystroke_buffer if e['event'] == 'press')
            while press_count > WINDOW_SIZE:
                e = self.keystroke_buffer.popleft()
                if e['event'] == 'press':
                    press_count -= 1

            total = sum(1 for e in self.keystroke_buffer if e['event'] == 'press')

            self.root.after(0, self.status_var.set,
                f"Collecting... {total}/{WINDOW_SIZE} keystrokes  ·  "
                f"Windows: {len(self.feature_windows)}/{TARGET_WIN}"
            )

            if self.new_since_last >= SLIDE_EVERY and total >= WINDOW_SIZE:
                features = extract_features(list(self.keystroke_buffer))
                self.new_since_last = 0
                if features is not None:
                    self.feature_windows.append({
                        'features'   : features,
                        'raw_events' : list(self.keystroke_buffer),
                    })
                    n = len(self.feature_windows)
                    self.root.after(0, self._draw_progress, n)
                    self.root.after(0, self.status_var.set,
                        f"Window {n}/{TARGET_WIN} captured  ·  "
                        f"WPM: {features[5]:.0f}  ·  Keep typing!"
                    )

        self.capture.stop()
        self._save()
        self.root.after(0, self.status_var.set,
            f"✓ Done! Data saved. You can close this window."
        )
        self.root.after(0, self.root.configure, {"bg": "#001a00"})

    def _save(self):
        data = {
            'name'           : self.name,
            'features'       : [w['features'] for w in self.feature_windows],
            'window_events'  : [w['raw_events'] for w in self.feature_windows],
            'all_raw_events' : self.all_raw_events,
            'window_size'    : WINDOW_SIZE,
            'n_windows'      : len(self.feature_windows),
            'captured_at'    : time.time(),
        }
        with open(OUTPUT_FILE, 'wb') as f:
            pickle.dump(data, f)
        size_kb = len(pickle.dumps(data)) / 1024
        print(f"[Friend] Saved {len(self.feature_windows)} windows ({size_kb:.1f} KB) → {OUTPUT_FILE}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    FriendEnrollWindow().run()
