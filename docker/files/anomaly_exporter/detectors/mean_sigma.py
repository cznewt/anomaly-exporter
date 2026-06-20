"""Classic mean +/- stddev z-score detector.

The non-robust, dependency-free sibling of ``zscore``: it uses the plain mean and
standard deviation of the training window instead of median + MAD. Cheapest of
all the detectors; best on clean, roughly-normal baselines where you don't need
outlier resistance.
"""
from __future__ import annotations

import pandas as pd

from .base import Detector


class MeanSigmaDetector(Detector):
    name = "mean_sigma"

    def point_scores(self, df, train_df, eval_df):
        z_max = float(self.params.get("z_max", 4))
        train = train_df["y"]
        mean = train.mean()
        std = train.std(ddof=0)
        if not std or pd.isna(std):  # flat baseline: neutral scale, never /0
            std = 1.0
        return [min(abs(a - mean) / std / z_max, 1.0) for a in eval_df["y"]]
