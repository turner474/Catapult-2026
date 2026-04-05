"""
simulate_typing.py
Simulates a slow, hesitant typist to test anomaly detection.
Uses pynput's Controller to inject keystrokes at realistic slow cadence.

The simulation mimics someone copying from another source:
- Lower WPM (20-35 vs your 60-90)
- Long pauses between words (looking away to read source)
- Irregular rhythm — hesitation before unfamiliar keys
- More consistent (less burst-y) inter-key intervals

Run AFTER enrolling your baseline. Open typing_window.py in exam mode first,
then run this script — it will type into whatever window has focus.

Usage:
    1. Run: python typing_window.py --mode exam --user demo
    2. Click the typing input box to focus it
    3. In a second terminal: python simulate_typing.py
"""

import time
import random
from pynput.keyboard import Controller, Key

keyboard = Controller()

# Free-form text the simulator types — slow and hesitant
PASSAGE = (
    "hello my name is john and i am typing this slowly. "
    "i am not sure what to write but i am trying my best here. "
    "the weather today is pretty nice i think. "
    "i went to the store earlier and bought some groceries. "
    "programming is interesting but sometimes confusing. "
    "i like to take my time when i type because i make mistakes. "
    "today has been a pretty normal day overall i would say. "
    "i am not a very fast typist as you can probably tell. "
    "sometimes i have to look at the keyboard to find the right keys. "
    "i hope this is enough text for the test to work properly."
)

# ------------------------------------------------------------------ #
#  Timing parameters — tweak these to change how "different" it feels #
# ------------------------------------------------------------------ #
STARTUP_DELAY = 2
DWELL_MEAN  = 0.08
DWELL_STD   = 0.02
FLIGHT_MEAN = 0.08
FLIGHT_STD  = 0.03
WORD_PAUSE_PROB = 0.05
WORD_PAUSE_MIN  = 0.1
WORD_PAUSE_MAX  = 0.3
SENTENCE_PAUSE_MIN = 0.2
SENTENCE_PAUSE_MAX = 0.4

def type_passage(passage: str):
    print(f"Starting in {STARTUP_DELAY} seconds — focus the typing window now...")
    for i in range(STARTUP_DELAY, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    print("Typing now.\n")

    for i, char in enumerate(passage):
        # --- Press key ---
        try:
            keyboard.press(char)
        except Exception:
            continue

        # --- Dwell time (hold key) ---
        dwell = max(0.04, random.gauss(DWELL_MEAN, DWELL_STD))
        time.sleep(dwell)

        # --- Release key ---
        keyboard.release(char)

        # --- Post-character flight time ---
        if char == '.':
            # Sentence boundary — long pause
            pause = random.uniform(SENTENCE_PAUSE_MIN, SENTENCE_PAUSE_MAX)
            print(f"  [sentence pause: {pause:.2f}s]")
            time.sleep(pause)
        elif char == ' ':
            # Word boundary — sometimes pause to "look at source"
            if random.random() < WORD_PAUSE_PROB:
                pause = random.uniform(WORD_PAUSE_MIN, WORD_PAUSE_MAX)
                time.sleep(pause)
            else:
                flight = max(0.05, random.gauss(FLIGHT_MEAN, FLIGHT_STD))
                time.sleep(flight)
        else:
            flight = max(0.05, random.gauss(FLIGHT_MEAN, FLIGHT_STD))
            time.sleep(flight)

        # Progress indicator every 50 chars
        if i > 0 and i % 50 == 0:
            pct = int((i / len(passage)) * 100)
            print(f"  {pct}% typed...")

    print("\nSimulation complete.")


if __name__ == "__main__":
    type_passage(PASSAGE)
