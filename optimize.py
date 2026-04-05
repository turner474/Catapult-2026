"""
optimize.py
Scores both your enrollment data and friend's data through
z-score and Isolation Forest independently, prints raw values
so you can decide how to weight each detector.

Usage: python optimize.py --user gabe3 --friend friend_features.pkl
"""

import argparse
import pickle
import numpy as np
from model import KeyGuardModel
from feature_extraction import FEATURE_NAMES

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user",   required=True)
    parser.add_argument("--friend", default="friend_features.pkl")
    args = parser.parse_args()

    # Load model
    model = KeyGuardModel(username=args.user)
    model.load()

    # Load friend data
    with open(args.friend, 'rb') as f:
        friend_data = pickle.load(f)
    friend_name     = friend_data['name']
    friend_features = friend_data['features']

    # Load your enrollment features from model stats
    # Re-score your enrollment windows by reloading pkl
    model_path = f"models/{args.user}.pkl"
    with open(model_path, 'rb') as f:
        raw = pickle.load(f)

    print(f"\n=== Detector Comparison: {args.user} vs {friend_name} ===\n")

    # Score friend
    friend_z_scores  = []
    friend_if_scores = []
    friend_z_flags   = []
    friend_if_flags  = []

    for fv in friend_features:
        r = model.score(np.array(fv))
        friend_z_scores.append(r['z_max'])
        friend_if_scores.append(r['if_raw'])
        friend_z_flags.append(r['z_flag'])
        friend_if_flags.append(r['if_flag'])

    print(f"--- {friend_name} ({len(friend_features)} windows) ---")
    print(f"{'Win':<5} {'Z-max':>8} {'Z-flag':>8} {'IF-raw':>10} {'IF-flag':>8}")
    print("-" * 45)
    for i, (z, zf, f, ff) in enumerate(zip(friend_z_scores, friend_if_scores, friend_z_flags, friend_if_flags)):
        print(f"  {i+1:<3} {z:>8.3f} {'FLAG' if zf else 'ok':>8} {f:>10.4f} {'FLAG' if ff else 'ok':>8}")

    print(f"\nZ-score  flagged: {sum(friend_z_flags)}/{len(friend_features)}")
    print(f"IForest  flagged: {sum(friend_if_flags)}/{len(friend_features)}")
    print(f"Both     flagged: {sum(a and b for a,b in zip(friend_z_flags, friend_if_flags))}/{len(friend_features)}")
    print(f"Either   flagged: {sum(a or b for a,b in zip(friend_z_flags, friend_if_flags))}/{len(friend_features)}")

    print(f"\n--- {args.user} self-test (enrollment mean as proxy) ---")
    print(f"Z-score threshold : ±2.5 std")
    print(f"IForest threshold : {model.if_threshold:.4f}")
    print(f"IForest mean score on friend: {np.mean(friend_if_scores):.4f}")
    print(f"Z-score mean max on friend : {np.mean(friend_z_scores):.4f}")

    print(f"\n--- Feature Separation ---")
    your_mean    = raw['enrollment_mean']
    your_std     = raw['enrollment_std']
    friend_mean  = np.mean([np.array(f) for f in friend_features], axis=0)

    print(f"{'Feature':<25} {'Your Mean':>10} {'Friend Mean':>12} {'Z-sep':>8}")
    print("-" * 60)
    for i, name in enumerate(FEATURE_NAMES[:6]):
        zsep = abs(friend_mean[i] - your_mean[i]) / max(your_std[i], 1e-9)
        print(f"  {name:<23} {your_mean[i]:>10.4f} {friend_mean[i]:>12.4f} {zsep:>8.2f}")

if __name__ == "__main__":
    main()
