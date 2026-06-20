"""EWMA control-band detector.

Builds a *causal* exponentially-weighted moving-average mean and an EWMA residual
sigma (each shifted one step, so a point is judged only against the points before
it), then scores each trailing point by how far it sits outside
``mean ± k·sigma``. Good for slowly drifting baselines where a fixed fence would
constantly trip; like the other lightweight detectors it has no seasonality model.
"""
from __future__ import annotations

import pandas as pd

from .base import Detector


class EwmaDetector(Detector):
    name = "ewma"

    def point_scores(self, df, train_df, eval_df):
        k = float(self.params.get("k", 3.0))
        alpha = self.params.get("alpha")
        span = self.params.get("span")
        ewm_kw = {"adjust": False}
        if alpha is not None:
            ewm_kw["alpha"] = float(alpha)
        else:
            ewm_kw["span"] = float(span) if span is not None else 12.0

        y = df["y"]
        pred = y.ewm(**ewm_kw).mean().shift(1)          # forecast from the past only
        sigma = (y - pred).pow(2).ewm(**ewm_kw).mean().pow(0.5).shift(1)

        scores = []
        for i in eval_df.index:
            p, s = pred.get(i), sigma.get(i)
            if p is None or s is None or pd.isna(p) or pd.isna(s) or s == 0:
                scores.append(0.0)
                continue
            scores.append(min(abs(y.loc[i] - p) / (k * s), 1.0))
        return scores
