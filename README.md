# KeyGuard

Continuous authentication via keystroke biometrics. Learns how you type, runs in the background, and locks out anyone else who sits down.

Built at Catapult Hacks 2026, Purdue University.

---

## What it does

Most security stops at login. KeyGuard protects what happens after. It captures 26 features from your typing rhythm during a 2-minute enrollment, then monitors continuously in the background. The moment someone with a different typing pattern takes over, it flags them and locks the session.

Everything runs locally. Nothing leaves your device.

---

## Installation

```bash
pip install pynput numpy scikit-learn
```

Python 3.9+, tested on Windows 11.

---

## Usage

```bash
# Main launcher
python main.py

# Enroll a user
python typing_window.py --mode enroll --user yourname

# Live monitoring
python typing_window.py --mode exam --user yourname

# Background daemon (monitors all keystrokes system-wide)
python daemon.py --user yourname

# Compare two users
python compare_window.py --user yourname

# Visualize typing fingerprint clusters
python visualize_embeddings.py --user yourname
```

---

## How it works

Keystroke events are captured via `pynput` with microsecond timestamps. The feature pipeline segments your typing into active bursts, ignoring idle time, and computes 26 features per window:

- Dwell time, inter-key flight time, pause rate, backspace rate, burst WPM
- Digraph timing for the 20 most common English letter pairs (th, he, in, er...)

Every 40 keystrokes a new window is scored against your enrolled baseline using an ensemble of three detectors. Two consecutive anomalous windows triggers an alert.

The model also updates itself continuously using exponential moving average with alpha=0.005. It only adapts on verified windows, so an intruder cannot slowly train it to accept them.

---

## Results

Validated against a real second user:

| Metric | Result |
|---|---|
| Detection rate | 20/20 windows (100%) |
| Isolation Forest score on intruder | 1.000 on all 20 windows |
| Top discriminating feature | Backspace rate (z-separation 4.12) |

---

## Files

| File | Purpose |
|---|---|
| `main.py` | Launcher UI |
| `typing_window.py` | Enrollment and live monitoring |
| `daemon.py` | Background daemon with alert popup |
| `keystroke_capture.py` | pynput listener, thread-safe buffer |
| `feature_extraction.py` | Burst segmentation, feature extraction |
| `model.py` | Isolation Forest + SVM + z-score ensemble |
| `compare_window.py` | Side-by-side user comparison |
| `visualize_embeddings.py` | PCA cluster visualization |
| `enroll_friend.py` | Capture a second user's data |
| `optimize.py` | Feature separation analysis |

---

## Built with

Python, pynput, scikit-learn, numpy, tkinter
