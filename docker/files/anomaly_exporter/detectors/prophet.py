"""Prophet forecast-band detector.

The heavyweight option: fits a Prophet model (trend + daily/weekly seasonality)
on the training window and scores how far the trailing points fall outside its
predicted uncertainty band. Reach for it when the metric has real trend or
seasonality; otherwise the lighter detectors are faster and dependency-free.
"""
from __future__ import annotations

import logging

from .base import Detector


def _parse_seasonality(value):
    """Prophet seasonality flag: 'auto', a bool, or an int number of terms."""
    v = str(value).strip().lower()
    if v == "auto":
        return "auto"
    if v in ("true", "1", "yes", "on"):
        return True
    if v in ("false", "0", "no", "off", ""):
        return False
    return int(v)


class ProphetDetector(Detector):
    name = "prophet"

    def point_scores(self, df, train_df, eval_df):
        from prophet import Prophet  # lazy: heavy import, only when actually scoring

        logging.getLogger("cmdstanpy").setLevel(logging.WARNING)  # silence the fitter
        model = Prophet(
            interval_width=float(self.params.get("interval_width", 0.95)),
            daily_seasonality=_parse_seasonality(self.params.get("daily_seasonality", "auto")),
            weekly_seasonality=_parse_seasonality(self.params.get("weekly_seasonality", "auto")),
        )
        model.fit(train_df[["ds", "y"]])
        forecast = model.predict(eval_df[["ds"]])
        lower = forecast["yhat_lower"].values
        upper = forecast["yhat_upper"].values

        scores = []
        for a, l, u in zip(eval_df["y"].values, lower, upper):
            if l <= a <= u:
                scores.append(0.0)
            else:
                band_width = (u - l) if u != l else 1.0
                scores.append(min(max(l - a, a - u) / band_width, 1.0))
        return scores
