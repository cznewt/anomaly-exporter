"""Shared detector scaffold.

A detector turns one Prometheus series (a list of ``[ts, value]`` pairs) into a
single ``0..1`` anomaly score. The shape is identical across every detector:
build a frame, refuse series with too little data, hold out the trailing
``eval_points`` as the scored window, score each held-out point ``0..1``, and
return the worst (max). Subclasses implement only ``point_scores``.
"""
from __future__ import annotations

import pandas as pd


class InsufficientData(Exception):
    """The series does not have enough points to score; skip it."""


def build_frame(values) -> pd.DataFrame:
    """A cleaned ``ds`` (datetime) / ``y`` (float) frame from Prometheus values."""
    df = pd.DataFrame(values, columns=["ds", "y"])
    df["ds"] = pd.to_datetime(df["ds"], unit="s")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    return df.dropna().reset_index(drop=True)


class Detector:
    name = "base"

    def __init__(self, module):
        # module is a config.Module; .params is the detector-specific block.
        self.module = module
        self.params = module.params

    def point_scores(self, df, train_df, eval_df):
        """Return a list of ``0..1`` scores, one per row of ``eval_df``."""
        raise NotImplementedError

    def score(self, values) -> float:
        eval_points = self.module.eval_points
        min_train = self.module.min_train_points
        df = build_frame(values)
        if len(df) < min_train + eval_points:
            raise InsufficientData(
                f"not enough points ({len(df)} < {min_train + eval_points})"
            )
        train_df = df.iloc[:-eval_points]
        eval_df = df.iloc[-eval_points:]
        scores = self.point_scores(df, train_df, eval_df)
        return float(max(scores)) if len(scores) else 0.0
