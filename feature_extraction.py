"""
feature_extraction.py
Burst-isolated feature extraction.

Instead of fixed time windows, we:
1. Split keystroke events into bursts (gaps > BURST_GAP_THRESHOLD = pause between bursts)
2. Compute timing features ONLY within bursts — ignores idle time between bursts
3. This makes features robust to real-world usage patterns

Features (26 total):
  Aggregate (6):
    0: mean_dwell        — avg key hold time within bursts
    1: std_dwell         — variance in dwell
    2: std_flight        — variance in inter-key intervals within bursts
    3: pause_rate        — fraction of within-burst gaps > SHORT_PAUSE threshold
    4: backspace_rate    — backspaces / total keypresses
    5: burst_wpm         — WPM computed only during active typing bursts

  Digraph (20):
    6-25: mean transition time for top 20 English digraphs
          Zero-filled if digraph not seen in window
"""

import numpy as np
from typing import Optional
from collections import deque

# ------------------------------------------------------------------ #
#  Thresholds                                                         #
# ------------------------------------------------------------------ #
BURST_GAP_THRESHOLD = 1.0    # seconds — gap larger than this = new burst
SHORT_PAUSE         = 0.3    # seconds — within-burst pause flag
MIN_KEYSTROKES      = 40     # minimum keystrokes to score a window
AVG_WORD_LEN        = 5

DIGRAPHS = [
    'th', 'he', 'in', 'er', 'an',
    're', 'on', 'en', 'at', 'es',
    'ed', 'te', 'ti', 'or', 'st',
    'ar', 'nd', 'to', 'it', 'is',
]


def extract_features(events: list) -> Optional[np.ndarray]:
    """
    Extract burst-isolated features from a list of keystroke events.
    Returns 26-dim feature vector or None if insufficient data.
    """
    if not events:
        return None

    presses  = sorted([e for e in events if e['event'] == 'press'],  key=lambda x: x['time'])
    releases = sorted([e for e in events if e['event'] == 'release'], key=lambda x: x['time'])

    if len(presses) < MIN_KEYSTROKES:
        return None

    # ── Segment into bursts ──────────────────────────────────────── #
    bursts = _segment_bursts(presses)

    if not bursts:
        return None

    # ── Compute features within bursts only ──────────────────────── #
    all_dwell   = []
    all_flight  = []
    all_pauses  = []
    burst_chars = 0
    burst_time  = 0.0

    release_map = {}
    for e in releases:
        release_map.setdefault(e['key'], []).append(e['time'])
    for k in release_map:
        release_map[k].sort()
    used_releases = {k: 0 for k in release_map}

    for burst in bursts:
        if len(burst) < 2:
            continue

        burst_chars += len(burst)
        burst_time  += burst[-1]['time'] - burst[0]['time']

        # Dwell times within burst
        for press in burst:
            k = press['key']
            if k not in release_map:
                continue
            ptr = used_releases[k]
            rel = release_map[k]
            while ptr < len(rel) and rel[ptr] < press['time']:
                ptr += 1
            if ptr < len(rel):
                d = rel[ptr] - press['time']
                if 0 < d < 1.0:
                    all_dwell.append(d)
                used_releases[k] = ptr + 1

        # Flight times within burst
        press_times = [e['time'] for e in burst]
        for i in range(len(press_times) - 1):
            ft = press_times[i+1] - press_times[i]
            if 0 < ft < BURST_GAP_THRESHOLD:
                all_flight.append(ft)
                if ft > SHORT_PAUSE:
                    all_pauses.append(ft)

    # ── Aggregate features ───────────────────────────────────────── #
    mean_dwell = float(np.mean(all_dwell))   if len(all_dwell)  > 1 else 0.0
    std_dwell  = float(np.std(all_dwell))    if len(all_dwell)  > 1 else 0.0
    std_flight = float(np.std(all_flight))   if len(all_flight) > 1 else 0.0
    pause_rate = float(len(all_pauses) / len(all_flight)) if all_flight else 0.0

    backspace_keys = {'Key.backspace', '\x08'}
    n_backspaces   = sum(1 for e in presses if e['key'] in backspace_keys)
    backspace_rate = float(n_backspaces / len(presses))

    # Burst WPM — only time spent actively typing
    if burst_time > 0:
        burst_wpm = float((burst_chars / AVG_WORD_LEN) / (burst_time / 60.0))
    else:
        burst_wpm = 0.0

    aggregate = np.array([
        mean_dwell,
        std_dwell,
        std_flight,
        pause_rate,
        backspace_rate,
        burst_wpm,
    ], dtype=np.float32)

    # ── Digraph features ─────────────────────────────────────────── #
    digraph_features = _compute_digraph_features(presses)

    return np.concatenate([aggregate, digraph_features]).astype(np.float32)


# ------------------------------------------------------------------ #
#  Burst segmentation                                                 #
# ------------------------------------------------------------------ #

def _segment_bursts(presses: list) -> list:
    """
    Split sorted press events into bursts.
    A new burst starts when gap between consecutive presses > BURST_GAP_THRESHOLD.
    Returns list of burst lists.
    """
    if not presses:
        return []

    bursts  = []
    current = [presses[0]]

    for i in range(1, len(presses)):
        gap = presses[i]['time'] - presses[i-1]['time']
        if gap > BURST_GAP_THRESHOLD:
            if len(current) >= 2:
                bursts.append(current)
            current = [presses[i]]
        else:
            current.append(presses[i])

    if len(current) >= 2:
        bursts.append(current)

    return bursts


# ------------------------------------------------------------------ #
#  Digraph timing                                                     #
# ------------------------------------------------------------------ #

def _compute_digraph_features(presses: list) -> np.ndarray:
    chars = []
    for e in sorted(presses, key=lambda x: x['time']):
        k = e['key']
        if k and len(k) == 1 and k.isprintable():
            chars.append((k.lower(), e['time']))

    digraph_times = {d: [] for d in DIGRAPHS}
    for i in range(len(chars) - 1):
        pair = chars[i][0] + chars[i+1][0]
        if pair in digraph_times:
            dt = chars[i+1][1] - chars[i][1]
            if 0.01 < dt < BURST_GAP_THRESHOLD:
                digraph_times[pair].append(dt)

    return np.array(
        [float(np.mean(t)) if t else 0.0 for d, t in digraph_times.items()],
        dtype=np.float32
    )


# ------------------------------------------------------------------ #
#  Feature names                                                      #
# ------------------------------------------------------------------ #
FEATURE_NAMES = [
    'mean_dwell', 'std_dwell', 'std_flight',
    'pause_rate', 'backspace_rate', 'burst_wpm',
] + [f'digraph_{d}' for d in DIGRAPHS]

N_AGG = 6  # number of aggregate features
