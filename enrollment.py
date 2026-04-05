"""
enrollment.py
Runs an enrollment session: captures keystroke windows, extracts features,
trains the Isolation Forest model, and saves it.

Can be run standalone (CLI) or imported and driven by the Tkinter UI.
"""

import time
import threading
from keystroke_capture import KeystrokeCapture
from feature_extraction import extract_features
from model import KeyGuardModel

# How long each feature window covers (seconds of typing)
WINDOW_DURATION_SEC = 15

# How many windows to collect during enrollment
# 15s * 8 windows = ~2 min of typing, gives the model good coverage
TARGET_WINDOWS = 8

# Minimum windows before we allow training (safety floor)
MIN_WINDOWS = 5


class EnrollmentSession:
    """
    Manages the enrollment flow.

    Usage (CLI / manual):
        session = EnrollmentSession(username="gabe")
        session.start()
        # ... user types ...
        session.stop()
        session.train_and_save()

    Usage (UI-driven with callbacks):
        session = EnrollmentSession(
            username="gabe",
            on_window_complete=lambda n, total: update_progress(n, total),
            on_done=lambda: show_done_screen(),
        )
        session.start()
    """

    def __init__(
        self,
        username: str,
        on_window_complete=None,   # callback(windows_collected, target)
        on_done=None,              # callback() when enrollment finishes
        on_error=None,             # callback(message: str)
    ):
        self.username = username
        self.on_window_complete = on_window_complete
        self.on_done = on_done
        self.on_error = on_error

        self.capture = KeystrokeCapture()
        self.feature_windows = []
        self._thread = None
        self._stop_event = threading.Event()
        self.model = KeyGuardModel(username=username)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def start(self):
        """Start enrollment in a background thread."""
        self.capture.start()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Force-stop enrollment early."""
        self._stop_event.set()
        self.capture.stop()

    def train_and_save(self):
        """
        Train model on collected windows and save.
        Call after stop() or after on_done fires.
        """
        if len(self.feature_windows) < MIN_WINDOWS:
            msg = (
                f"Only {len(self.feature_windows)} windows collected "
                f"(need {MIN_WINDOWS}). Type more during enrollment."
            )
            if self.on_error:
                self.on_error(msg)
            else:
                raise RuntimeError(msg)
            return False

        self.model.train(self.feature_windows)
        self.model.save()
        return True

    # ------------------------------------------------------------------ #
    #  Internal loop                                                       #
    # ------------------------------------------------------------------ #

    def _run(self):
        """
        Background thread: collect windows until target reached or stopped.
        Each window = WINDOW_DURATION_SEC seconds of typing.
        """
        windows_collected = 0

        while not self._stop_event.is_set():
            # Wait one window duration, collecting keystrokes
            deadline = time.time() + WINDOW_DURATION_SEC
            while time.time() < deadline and not self._stop_event.is_set():
                time.sleep(0.1)

            # Drain events and extract features
            events = self.capture.flush()
            features = extract_features(events)

            if features is not None:
                self.feature_windows.append(features)
                windows_collected += 1

                if self.on_window_complete:
                    self.on_window_complete(windows_collected, TARGET_WINDOWS)

                print(
                    f"[Enrollment] Window {windows_collected}/{TARGET_WINDOWS} captured. "
                    f"WPM={features[7]:.1f}, pause_rate={features[4]:.3f}"
                )
            else:
                print(
                    f"[Enrollment] Window skipped — not enough keystrokes. "
                    f"Keep typing!"
                )

            if windows_collected >= TARGET_WINDOWS:
                break

        self.capture.stop()

        if self.on_done:
            self.on_done()


# ------------------------------------------------------------------ #
#  CLI entry point — run standalone to enroll from terminal          #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    import sys

    username = input("Enter your username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    print(f"\nEnrolling '{username}'...")
    print(f"You will type for {TARGET_WINDOWS} x {WINDOW_DURATION_SEC}s windows (~{TARGET_WINDOWS * WINDOW_DURATION_SEC // 60} min).")
    print("Type naturally — anything you want. Stream of consciousness is fine.")
    print("Starting in 3 seconds...\n")
    time.sleep(3)

    def on_window(n, total):
        bar = "█" * n + "░" * (total - n)
        print(f"  Progress: [{bar}] {n}/{total} windows")

    def on_done():
        print("\nEnrollment capture complete. Training model...")

    session = EnrollmentSession(
        username=username,
        on_window_complete=on_window,
        on_done=on_done,
    )
    session.start()
    session._thread.join()  # wait for capture to finish

    success = session.train_and_save()
    if success:
        print(f"\nModel saved. '{username}' is enrolled.")
        print("You can now run exam mode.")
