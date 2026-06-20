"""Holt-Winters (triple exponential smoothing) seasonal detector.

A lighter, seasonality-aware alternative to Prophet: fit Holt-Winters on the
training window, forecast the trailing window, and score each point against a
band of ``k`` residual-sigmas around the forecast. Set ``season_length`` to the
number of steps in one cycle (e.g. 288 for a day at 5m resolution); leave it at 0
for a trend-only fit. Far cheaper than Prophet (no Stan / cmdstan), but needs a
roughly regular series and at least two full seasons of training data.
"""
from __future__ import annotations

import pandas as pd

from .base import Detector


class HoltWintersDetector(Detector):
    name = "holt_winters"

    def point_scores(self, df, train_df, eval_df):
        from statsmodels.tsa.holtwinters import ExponentialSmoothing  # lazy import

        k = float(self.params.get("k", 3.0))
        season_length = int(self.params.get("season_length", 0) or 0)
        trend = self.params.get("trend", "add")
        if trend in (None, "none", "None", ""):
            trend = None

        train = train_df["y"].reset_index(drop=True).astype(float)
        kwargs = {"trend": trend, "initialization_method": "estimated"}
        # Only ask for a seasonal component when there's enough data to fit it.
        if season_length and len(train) >= 2 * season_length:
            kwargs["seasonal"] = self.params.get("seasonal", "add")
            kwargs["seasonal_periods"] = season_length

        model = ExponentialSmoothing(train, **kwargs).fit()
        forecast = pd.Series(model.forecast(len(eval_df))).reset_index(drop=True).values
        resid_std = float((model.fittedvalues - train).std(ddof=0))
        band = k * resid_std if resid_std else 1.0  # guard a perfect fit

        actual = eval_df["y"].reset_index(drop=True).astype(float).values
        return [min(abs(a - f) / band, 1.0) for a, f in zip(actual, forecast)]
