"""
compare_models.py
Compare two enrolled user models — shows how similar their baselines are.

Usage: python compare_models.py --user1 gabe4 --user2 gabetest1
"""

import argparse
import pickle
import numpy as np
from feature_extraction import FEATURE_NAMES

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user1", required=True)
    parser.add_argument("--user2", required=True)
    args = parser.parse_args()

    models = {}
    for user in [args.user1, args.user2]:
        with open(f"models/{user}.pkl", 'rb') as f:
            models[user] = pickle.load(f)

    m1 = models[args.user1]
    m2 = models[args.user2]

    print(f"\n=== Model Comparison: {args.user1} vs {args.user2} ===\n")
    print(f"{'Feature':<25} {args.user1:>12} {args.user2:>12} {'Diff':>10} {'Z-sep':>8}")
    print("-" * 72)

    for i, name in enumerate(FEATURE_NAMES[:6]):
        v1   = m1['enrollment_mean'][i]
        v2   = m2['enrollment_mean'][i]
        std  = (m1['enrollment_std'][i] + m2['enrollment_std'][i]) / 2
        diff = abs(v1 - v2)
        zsep = diff / max(std, 1e-9)
        flag = " ← different" if zsep > 1.5 else ""
        print(f"  {name:<23} {v1:>12.4f} {v2:>12.4f} {diff:>10.4f} {zsep:>8.2f}{flag}")

    print(f"\n--- Digraph comparison ---")
    for i in range(6, min(26, len(FEATURE_NAMES))):
        name = FEATURE_NAMES[i]
        v1   = m1['enrollment_mean'][i]
        v2   = m2['enrollment_mean'][i]
        std  = (m1['enrollment_std'][i] + m2['enrollment_std'][i]) / 2
        if v1 < 0.001 and v2 < 0.001:
            continue
        zsep = abs(v1 - v2) / max(std, 1e-9)
        if zsep > 1.0:
            print(f"  {name:<23} {v1:>12.4f} {v2:>12.4f} z={zsep:.2f} ← different")

    print(f"\n--- Summary ---")
    diffs = []
    for i in range(6):
        v1  = m1['enrollment_mean'][i]
        v2  = m2['enrollment_mean'][i]
        std = (m1['enrollment_std'][i] + m2['enrollment_std'][i]) / 2
        diffs.append(abs(v1 - v2) / max(std, 1e-9))
    print(f"Avg z-separation across aggregate features: {np.mean(diffs):.2f}")
    print(f"If < 0.5 — models are very similar (good, consistent typing)")
    print(f"If > 1.5 — models differ significantly (one enrollment was off)")

if __name__ == "__main__":
    main()
