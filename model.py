"""
model.py
Ensemble anomaly detector:

  Layer 1: Z-score on selected features (statistical)
  Layer 2: Isolation Forest (ML — trained on enrollment baseline)
  Layer 3: Mahalanobis distance (display only)
  Layer 4: One-Class SVM (display only)

Primary decision: weighted vote between Z-score and Isolation Forest.
Both must agree to flag (reduces false positives).
"""

import os
import pickle
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler

MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

# Z-score settings
Z_THRESHOLD   = 2.5
AGG_MASK      = [2, 3, 4, 5, 6, 25, 13]

# Isolation Forest settings
IF_CONTAMINATION = 0.05
IF_ESTIMATORS    = 200

# Voting — both z-score AND iforest must agree
VOTES_TO_FLAG    = 2

# Display only
MAHAL_PERCENTILE = 97
SVM_NU           = 0.15


class KeyGuardModel:

    def __init__(self, username: str):
        self.username        = username
        self.enrollment_mean = None
        self.enrollment_std  = None
        self.cov_inv         = None
        self.mahal_threshold = None
        self.if_threshold    = None
        self.scaler          = StandardScaler()
        self.iforest         = IsolationForest(
            n_estimators=IF_ESTIMATORS,
            contamination=IF_CONTAMINATION,
            random_state=42,
        )
        self.svm             = OneClassSVM(nu=SVM_NU, kernel='rbf', gamma='scale')
        self.trained         = False
        self.n_features      = None

    def train(self, feature_vectors: list):
        if len(feature_vectors) < 5:
            raise ValueError(f"Need at least 5 windows. Got {len(feature_vectors)}.")

        X = np.array(feature_vectors, dtype=np.float64)
        self.n_features      = X.shape[1]

        # Z-score stats
        self.enrollment_mean = np.mean(X, axis=0)
        self.enrollment_std  = np.std(X, axis=0)
        self.enrollment_std  = np.where(self.enrollment_std < 1e-9, 1e-9, self.enrollment_std)

        # Mahalanobis
        self.cov_inv         = self._safe_cov_inv(X)
        train_distances      = [self._mahalanobis(x) for x in X]
        self.mahal_threshold = float(np.percentile(train_distances, MAHAL_PERCENTILE))

        # Isolation Forest — train on scaled features
        X_scaled = self.scaler.fit_transform(X)
        self.iforest.fit(X_scaled)

        # Set IF threshold from training scores
        if_scores = -self.iforest.score_samples(X_scaled)
        self.if_threshold = float(np.mean(if_scores) + 2 * np.std(if_scores))

        # SVM display only
        self.svm.fit(X_scaled)
        self.trained = True

        print(f"[Model] Trained on {len(feature_vectors)} windows.")
        print(f"[Model] Z-score   — mask: {AGG_MASK}, threshold: ±{Z_THRESHOLD}")
        print(f"[Model] IForest   — threshold: {self.if_threshold:.4f}")
        print(f"[Model] Mahal     — threshold: {self.mahal_threshold:.4f} [DISPLAY]")
        print(f"[Model] Votes to flag: {VOTES_TO_FLAG}/2 (z-score + iforest)")

        fps = sum(1 for x in feature_vectors if self.score(x)['is_anomaly'])
        print(f"[Model] False positives on training data: {fps}/{len(feature_vectors)}")

    def score(self, feature_vector: np.ndarray) -> dict:
        if not self.trained:
            raise RuntimeError("Model not trained.")

        x = np.array(feature_vector, dtype=np.float64)

        # Z-score
        x_sel    = x[AGG_MASK]
        m_sel    = self.enrollment_mean[AGG_MASK]
        s_sel    = self.enrollment_std[AGG_MASK]
        z_scores = np.abs((x_sel - m_sel) / s_sel)
        z_flag   = bool(np.any(z_scores > Z_THRESHOLD))
        z_max    = float(np.max(z_scores))
        z_worst  = int(AGG_MASK[int(np.argmax(z_scores))])

        # Isolation Forest
        x_scaled  = self.scaler.transform(x.reshape(1, -1))
        if_raw    = float(-self.iforest.score_samples(x_scaled)[0])
        if_flag   = if_raw > self.if_threshold

        # Mahalanobis display only
        mahal_dist = self._mahalanobis(x)
        mahal_flag = mahal_dist > self.mahal_threshold

        # SVM display only
        svm_flag = self.svm.predict(x_scaled)[0] == -1

        # Primary decision: z-score AND iforest
        votes      = int(z_flag) + int(if_flag)
        is_anomaly = votes >= VOTES_TO_FLAG

        # Normalized score for display
        z_norm     = min(z_max / (Z_THRESHOLD * 2), 1.0)
        if_norm    = min(if_raw / (self.if_threshold * 2), 1.0)
        anomaly_score = float(0.5 * z_norm + 0.5 * if_norm)

        return {
            'anomaly_score'   : anomaly_score,
            'is_anomaly'      : is_anomaly,
            'votes'           : votes,
            'z_flag'          : z_flag,
            'z_max'           : z_max,
            'z_raw'           : z_max,
            'z_worst_feature' : z_worst,
            'z_scores'        : z_scores.tolist(),
            'if_flag'         : if_flag,
            'if_raw'          : if_raw,
            'if_threshold'    : self.if_threshold,
            'mahal_dist'      : float(mahal_dist),
            'mahal_threshold' : self.mahal_threshold,
            'svm_flag'        : svm_flag,
            'threshold'       : 0.5,
        }

    def save(self):
        path = self._model_path()
        with open(path, 'wb') as f:
            pickle.dump({
                'username'        : self.username,
                'enrollment_mean' : self.enrollment_mean,
                'enrollment_std'  : self.enrollment_std,
                'cov_inv'         : self.cov_inv,
                'mahal_threshold' : self.mahal_threshold,
                'if_threshold'    : self.if_threshold,
                'scaler'          : self.scaler,
                'iforest'         : self.iforest,
                'svm'             : self.svm,
                'n_features'      : self.n_features,
                'trained'         : self.trained,
            }, f)
        print(f"[Model] Saved to {path}")

    def load(self):
        path = self._model_path()
        if not os.path.exists(path):
            raise FileNotFoundError(f"No model for '{self.username}'. Enroll first.")
        with open(path, 'rb') as f:
            d = pickle.load(f)
        if 'enrollment_mean' not in d:
            raise ValueError(f"Old model format. Re-enroll user '{self.username}'.")
        self.enrollment_mean = d['enrollment_mean']
        self.enrollment_std  = d['enrollment_std']
        self.cov_inv         = d['cov_inv']
        self.mahal_threshold = d['mahal_threshold']
        self.if_threshold    = d['if_threshold']
        self.scaler          = d['scaler']
        self.iforest         = d['iforest']
        self.svm             = d['svm']
        self.n_features      = d['n_features']
        self.trained         = d['trained']
        print(f"[Model] Loaded '{self.username}'")
        print(f"[Model] Z-score threshold: ±{Z_THRESHOLD} on features {AGG_MASK}")
        print(f"[Model] IForest threshold: {self.if_threshold:.4f}")

    def model_exists(self) -> bool:
        return os.path.exists(self._model_path())

    def _mahalanobis(self, x: np.ndarray) -> float:
        diff = x - self.enrollment_mean
        return float(np.sqrt(np.abs(diff @ self.cov_inv @ diff)))

    def _safe_cov_inv(self, X: np.ndarray) -> np.ndarray:
        try:
            cov = np.cov(X.T)
            cov += np.eye(cov.shape[0]) * 1e-6
            return np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            var = np.var(X, axis=0)
            var = np.where(var < 1e-9, 1e-9, var)
            return np.diag(1.0 / var)

    def _model_path(self) -> str:
        return os.path.join(MODEL_DIR, f"{self.username}.pkl")


    def adapt(self, feature_vector: np.ndarray, alpha: float = 0.005):
        """
        Online learning — exponential moving average update to enrollment baseline.
        
        alpha = 0.005 means each new window contributes 0.5% to the baseline.
        At 1 window per 40 keystrokes, 75 WPM typing updates baseline ~1% per minute.
        Full session drift is barely perceptible but real — model slowly adapts
        to time-of-day fatigue, keyboard familiarity, and long-term typing evolution.
        
        Drift protection: only adapts if window is NOT anomalous (don't learn intruders).
        """
        if not self.trained:
            return

        x = np.array(feature_vector, dtype=np.float64)

        # Only adapt on clean windows — prevents adversarial drift
        result = self.score(x)
        if result['is_anomaly']:
            return

        # EMA update on mean and std
        self.enrollment_mean = (1 - alpha) * self.enrollment_mean + alpha * x
        
        # Update std via EMA on squared deviation
        deviation = (x - self.enrollment_mean) ** 2
        self.enrollment_std = np.sqrt(
            (1 - alpha) * self.enrollment_std ** 2 + alpha * deviation
        )
        # Floor to prevent collapse
        self.enrollment_std = np.where(
            self.enrollment_std < 1e-9, 1e-9, self.enrollment_std
        )
