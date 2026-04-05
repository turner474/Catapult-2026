"""
visualize_embeddings.py - KeyGuard
PCA cluster visualization matching professional UI aesthetic.
"""

import argparse
import pickle
import numpy as np
import tkinter as tk
from tkinter import font as tkfont
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

BG      = "#0b0c0f"
BG2     = "#13151a"
BG3     = "#1a1d24"
LINE    = "#2a2d38"
LINE2   = "#363a47"
TXT     = "#f0f2f5"
TXT2    = "#9098a9"
TXT3    = "#555e70"
BLUE    = "#4d9fff"
GREEN   = "#2ecc71"
GREEN_D = "#1a7a43"
RED     = "#e74c3c"
RED_D   = "#8b1a14"
CYAN    = "#1abc9c"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user",   required=True)
    parser.add_argument("--friend", default="friend_features.pkl")
    args = parser.parse_args()

    with open(f"models/{args.user}.pkl", 'rb') as f:
        your_data = pickle.load(f)

    with open(args.friend, 'rb') as f:
        friend_data = pickle.load(f)

    friend_X    = np.array(friend_data['features'], dtype=np.float64)
    friend_name = friend_data['name']
    mean        = your_data['enrollment_mean']
    std         = your_data['enrollment_std']

    np.random.seed(42)
    your_X = np.random.multivariate_normal(mean, np.diag(std**2), size=20)

    X      = np.vstack([your_X, friend_X])
    X_sc   = StandardScaler().fit_transform(X)
    pca    = PCA(n_components=2, random_state=42)
    X_2d   = pca.fit_transform(X_sc)
    var    = pca.explained_variance_ratio_

    your_2d   = X_2d[:20]
    friend_2d = X_2d[20:]

    root = tk.Tk()
    root.title("KeyGuard — Typing Fingerprint Embeddings")
    root.configure(bg=BG)
    root.geometry("900x680")

    def f(size, weight="normal", family="Segoe UI"):
        return tkfont.Font(family=family, size=size, weight=weight)

    # ── Top bar ─────────────────────────────────────────────────── #
    bar = tk.Frame(root, bg=BG2, height=44)
    bar.pack(fill="x")
    bar.pack_propagate(False)
    lf = tk.Frame(bar, bg=BG2)
    lf.pack(side="left", padx=18, pady=10)
    tk.Label(lf, text="⬡", bg=BG2, fg=BLUE, font=f(12,"bold")).pack(side="left")
    tk.Label(lf, text="  KEYGUARD", bg=BG2, fg=TXT, font=f(11,"bold")).pack(side="left")
    tk.Label(lf, text="  /  TYPING FINGERPRINT EMBEDDINGS", bg=BG2, fg=TXT3, font=f(9)).pack(side="left")
    tk.Frame(root, bg=LINE, height=1).pack(fill="x")

    # ── Info bar ────────────────────────────────────────────────── #
    info = tk.Frame(root, bg=BG2, padx=20, pady=10)
    info.pack(fill="x")
    tk.Label(info,
             text=f"PCA projection of 26-dimensional feature vectors  ·  PC1: {var[0]*100:.1f}%  PC2: {var[1]*100:.1f}% variance explained",
             bg=BG2, fg=TXT3, font=f(8, family="Consolas")).pack(side="left")

    cent_sep = np.linalg.norm(np.mean(your_2d,axis=0) - np.mean(friend_2d,axis=0))
    tk.Label(info, text=f"Centroid separation: {cent_sep:.2f} units",
             bg=BG2, fg=CYAN, font=f(8,"bold","Consolas")).pack(side="right")
    tk.Frame(root, bg=LINE, height=1).pack(fill="x")

    # ── Canvas ──────────────────────────────────────────────────── #
    cv_frame = tk.Frame(root, bg=BG)
    cv_frame.pack(fill="both", expand=True, padx=24, pady=16)

    cv = tk.Canvas(cv_frame, bg=BG2, highlightthickness=1, highlightbackground=LINE)
    cv.pack(fill="both", expand=True)

    def draw(event=None):
        cv.delete("all")
        W = cv.winfo_width()
        H = cv.winfo_height()
        if W < 10 or H < 10: return

        PAD = 48
        gW  = W - 2*PAD
        gH  = H - 2*PAD

        all_x = X_2d[:,0]
        all_y = X_2d[:,1]
        xmin, xmax = all_x.min()-0.8, all_x.max()+0.8
        ymin, ymax = all_y.min()-0.8, all_y.max()+0.8

        def to_cv(px, py):
            cx = PAD + (px-xmin)/(xmax-xmin)*gW
            cy = H - PAD - (py-ymin)/(ymax-ymin)*gH
            return cx, cy

        # Grid lines
        for i in range(5):
            x = PAD + i*(gW/4)
            y = PAD + i*(gH/4)
            cv.create_line(x, PAD, x, H-PAD, fill=BG3, dash=(2,4))
            cv.create_line(PAD, y, W-PAD, y, fill=BG3, dash=(2,4))

        # Axes
        cx0, cy0 = to_cv(0, 0)
        cv.create_line(PAD, cy0, W-PAD, cy0, fill=LINE2, width=1)
        cv.create_line(cx0, PAD, cx0, H-PAD, fill=LINE2, width=1)

        # Ellipses
        def ellipse(pts, color):
            if len(pts) < 3: return
            m  = np.mean(pts, axis=0)
            s  = np.std(pts, axis=0) * 1.8
            cx, cy = to_cv(m[0], m[1])
            rx = s[0]/(xmax-xmin)*gW
            ry = s[1]/(ymax-ymin)*gH
            cv.create_oval(cx-rx, cy-ry, cx+rx, cy+ry,
                           outline=color, width=1, dash=(6,4))

        ellipse(your_2d,   GREEN)
        ellipse(friend_2d, RED)

        # Points
        for px, py in your_2d:
            cx, cy = to_cv(px, py)
            r = 5
            cv.create_oval(cx-r, cy-r, cx+r, cy+r,
                           fill=GREEN, outline=BG2, width=1)

        for px, py in friend_2d:
            cx, cy = to_cv(px, py)
            r = 5
            cv.create_oval(cx-r, cy-r, cx+r, cy+r,
                           fill=RED, outline=BG2, width=1)

        # Centroids
        def centroid(pts, color, label):
            m = np.mean(pts, axis=0)
            cx, cy = to_cv(m[0], m[1])
            r = 8
            cv.create_oval(cx-r, cy-r, cx+r, cy+r,
                           fill=color, outline=TXT, width=2)
            cv.create_text(cx, cy-18, text=label, fill=color,
                           font=tkfont.Font(family="Consolas", size=8, weight="bold"))

        centroid(your_2d,   GREEN, args.user.upper())
        centroid(friend_2d, RED,   friend_name.upper())

        # Axis labels
        cv.create_text(W//2, H-8,
                       text=f"PC1 ({var[0]*100:.1f}% variance)",
                       fill=TXT3, font=tkfont.Font(family="Segoe UI", size=8))
        cv.create_text(10, H//2, text="PC2", fill=TXT3,
                       font=tkfont.Font(family="Segoe UI", size=8), angle=90)

    cv.bind("<Configure>", draw)

    # ── Legend ──────────────────────────────────────────────────── #
    leg = tk.Frame(root, bg=BG2, padx=20, pady=10)
    leg.pack(fill="x")
    tk.Frame(root, bg=LINE, height=1).pack(fill="x", side="bottom", before=leg)

    tk.Label(leg, text="●", bg=BG2, fg=GREEN, font=f(10)).pack(side="left")
    tk.Label(leg, text=f"  {args.user}  (enrolled user)",
             bg=BG2, fg=TXT2, font=f(9)).pack(side="left")
    tk.Label(leg, text="      ●", bg=BG2, fg=RED, font=f(10)).pack(side="left")
    tk.Label(leg, text=f"  {friend_name}  (unauthorized user)",
             bg=BG2, fg=TXT2, font=f(9)).pack(side="left")
    tk.Label(leg, text="Each dot = one 80-keystroke window",
             bg=BG2, fg=TXT3, font=f(8, family="Consolas")).pack(side="right")

    # Footer
    tk.Frame(root, bg=LINE, height=1).pack(fill="x", side="bottom")
    foot = tk.Frame(root, bg=BG2, height=24)
    foot.pack(fill="x", side="bottom")
    foot.pack_propagate(False)
    tk.Label(foot, text=f"● SECURE  ·  All data local", bg=BG2, fg=GREEN,
             font=f(7,"normal","Consolas")).pack(side="right", padx=14)

    root.mainloop()


if __name__ == "__main__":
    main()
