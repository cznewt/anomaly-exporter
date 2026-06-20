"""Robust (median + MAD) z-score detector."""
from __future__ import annotations

import pandas as pd

from .base import Detector

# median(|x - median(x)|) * this == 1 std for a normal distribution.
_MAD_TO_SIGMA = 1.4826


class ZScoreDetector(Detector):
    """Score trailing points by robust standard deviations from the baseline.

    Median + MAD (from the training window) make the baseline outlier-resistant;
    the score is a smooth ``0..1`` ramp that hits ``1.0`` at ``z_max`` sigmas.
    """

    name = "zscore"

    def point_scores(self, df, train_df, eval_df):
        z_max = float(self.params.get("z_max", 4))
        train = train_df["y"]
        median = train.median()
        mad = (train - median).abs().median()
        scale = _MAD_TO_SIGMA * mad
        if scale == 0:  # near-constant baseline: fall back to std, then neutral
            scale = train.std(ddof=0)
            if not scale or pd.isna(scale):
                scale = 1.0
        return [min(abs(a - median) / scale / z_max, 1.0) for a in eval_df["y"]]
