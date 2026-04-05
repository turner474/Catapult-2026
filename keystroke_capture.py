"""
keystroke_capture.py
Captures raw keystroke events with high-resolution timestamps.
Stores: key, event_type (press/release), timestamp (seconds, float)
"""

import time
import threading
from collections import deque
from pynput import keyboard


class KeystrokeCapture:
    """
    Captures keypress and keyrelease events with timestamps.
    Runs in a background thread. Thread-safe event buffer.
    """

    def __init__(self, max_buffer=10000):
        # Each event: {'key': str, 'event': 'press'|'release', 'time': float}
        self.events = deque(maxlen=max_buffer)
        self._listener = None
        self._lock = threading.Lock()
        self.running = False

    # ------------------------------------------------------------------ #
    #  Internal handlers                                                   #
    # ------------------------------------------------------------------ #

    def _normalize_key(self, key) -> str:
        """Convert pynput key object to a consistent string."""
        try:
            return key.char  # regular character
        except AttributeError:
            return str(key)  # special key like Key.backspace

    def _on_press(self, key):
        t = time.perf_counter()
        k = self._normalize_key(key)
        with self._lock:
            self.events.append({'key': k, 'event': 'press', 'time': t})

    def _on_release(self, key):
        t = time.perf_counter()
        k = self._normalize_key(key)
        with self._lock:
            self.events.append({'key': k, 'event': 'release', 'time': t})

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def start(self):
        """Start capturing keystrokes in background thread."""
        if self.running:
            return
        self.running = True
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.start()

    def stop(self):
        """Stop capturing."""
        if self._listener:
            self._listener.stop()
        self.running = False

    def flush(self) -> list:
        """
        Return all buffered events and clear the buffer.
        Call this periodically to drain events into the feature pipeline.
        """
        with self._lock:
            events = list(self.events)
            self.events.clear()
        return events

    def peek(self) -> list:
        """Return buffered events WITHOUT clearing (for inspection)."""
        with self._lock:
            return list(self.events)

    def clear(self):
        """Discard all buffered events."""
        with self._lock:
            self.events.clear()
