# KeyGuard — Continuous Authentication via Keystroke Biometrics

> Your typing fingerprint. On your device. Always.

KeyGuard is a local-first continuous authentication system that detects unauthorized users by analyzing keystroke behavioral biometrics. It learns your unique typing fingerprint during enrollment, then silently monitors all keystrokes to verify it's still you — no camera, no extra hardware, no cloud.

---

## Demo

[Video Demo](#) | [Devpost Submission](#)

---

## How It Works

1. **Enroll** — type freely for 2 minutes. KeyGuard captures 16 windows of 80 keystrokes each and extracts 26 behavioral features including dwell time, inter-key flight time, pause rate, and digraph timing — how fast your fingers move between specific letter pairs like T-H or I-S.

2. **Monitor** — KeyGuard runs silently in the background. Every 40 keystrokes it scores a new window against your baseline using an ensemble of three detectors: Z-score anomaly detection, Isolation Forest, and One-Class SVM.

3. **Alert** — two consecutive anomalous windows triggers a security alert and optionally locks the session.

---

## Features

- Ensemble of Isolation Forest + One-Class SVM trained entirely on-device
- Online learning via exponential moving average — model adapts to your typing over time without ever learning an intruder's patterns
- Digraph timing features — 20 letter-pair transition times capturing neuromuscular finger coordination
- Burst-isolated feature extraction — ignores idle time, only measures active typing
- Sliding window accumulator — scores every 40 keystrokes for continuous coverage
- Background daemon — monitors system-wide across all applications
- PCA visualization of typing fingerprint clusters
- Side-by-side user comparison tool
- Empirical feature optimization against held-out user data

---

## Validation

Two-person validation (enrolled user vs held-out unauthorized user):

| Metric | Result |
|---|---|
| Detection rate (unauthorized user) | 20/20 windows (100%) |
| False positive rate (enrolled user) | ~1/10 windows |
| Isolation Forest score on unauthorized user | 1.000 (maximum) on all 20 windows |
| PCA centroid separation | 3.62 units |
| Key discriminating features | backspace rate (z=4.12), digraph:th (z=2.17), digraph:is (z=2.07) |

---

## Installation

```bash
pip install pynput numpy scikit-learn
```

Requires Python 3.9+. Tested on Windows 11.

---

## Usage

```bash
# Launch the full UI
python main.py

# Enroll a user
python typing_window.py --mode enroll --user yourname

# Start live monitoring
python typing_window.py --mode exam --user yourname

# Run background daemon (monitors all keystrokes system-wide)
python daemon.py --user yourname

# Compare two users side by side
python compare_window.py --user yourname

# Visualize PCA clusters
python visualize_embeddings.py --user yourname

# Optimize feature mask against a second user
python optimize.py --user yourname
```

---

## Architecture

```
keystroke_capture.py     # pynput background listener, thread-safe buffer
feature_extraction.py    # burst segmentation, 26-dim feature extraction
model.py                 # Isolation Forest + One-Class SVM + z-score ensemble
typing_window.py         # live monitoring UI with real-time anomaly graph
daemon.py                # silent background daemon, alert popup, session lock
main.py                  # launcher UI
compare_window.py        # side-by-side user comparison
visualize_embeddings.py  # PCA cluster visualization
enroll_friend.py         # capture second user's typing data
optimize.py              # feature separation analysis and mask optimization
```

---

## Privacy

All biometric data is stored locally in `models/` as `.pkl` files. No data is ever transmitted externally. Key content is never captured — only keystroke timing metadata. Compliant with FERPA, HIPAA, and enterprise zero-trust requirements.

---

## Target Markets

- **Healthcare** — HIPAA-compliant shared workstation authentication in clinical environments
- **Government / Defense** — zero-trust endpoint auth with no cloud dependency
- **Financial** — continuous session verification for shared banking terminals
- **Enterprise** — insider threat detection and remote work security

---

## Built At

Catapult Hacks 2026 · ML@Purdue · Gabriel Turner · Purdue University
