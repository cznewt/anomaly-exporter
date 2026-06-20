"""IQR (Tukey-fence) detector."""
from __future__ import annotations

from .base import Detector


class IqrDetector(Detector):
    """Score trailing points by how far they fall outside a robust IQR fence.

    The fence ``[Q1 - k*IQR, Q3 + k*IQR]`` comes from the training window, so the
    most recent points are judged against an unspoiled baseline. Training-free
    and robust to baseline outliers, but seasonality-naive.
    """

    name = "iqr"

    def point_scores(self, df, train_df, eval_df):
        k = float(self.params.get("k", 1.5))
        train = train_df["y"]
        q1, q3 = train.quantile(0.25), train.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - k * iqr, q3 + k * iqr
        band_width = (upper - lower) if upper != lower else 1.0  # guard flat series

        scores = []
        for a in eval_df["y"]:
            if lower <= a <= upper:
                scores.append(0.0)
            else:
                scores.append(min(max(lower - a, a - upper) / band_width, 1.0))
        return scores
