import math

import pytest

from anomaly_exporter.config import Module
from anomaly_exporter.detectors import DETECTORS, InsufficientData


def make_series(values, step=60):
    return [[i * step, v] for i, v in enumerate(values)]


def mod(detector, **params):
    return Module(
        name="t", detector=detector, lookback=3600, step="1m",
        eval_points=5, min_train_points=20, params=params,
    )


def baseline(n=80):
    # smooth sine + small deterministic noise: variance > 0 (EWMA needs sigma),
    # but the trailing points are a normal continuation, not outliers.
    return [100 + 5 * math.sin(i / 6.0) + ((i * 29) % 7 - 3) * 0.2 for i in range(n)]


# Lightweight, dependency-free detectors share the same train/eval scaffold.
LIGHT = ["iqr", "zscore", "mean_sigma", "ewma"]
CLEAN_MAX = {"iqr": 0.3, "zscore": 0.5, "mean_sigma": 0.5, "ewma": 0.8}


@pytest.mark.parametrize("name", LIGHT)
def test_clean_series_scores_low(name):
    score = DETECTORS[name](mod(name)).score(make_series(baseline()))
    assert score <= CLEAN_MAX[name], f"{name} clean score {score}"


@pytest.mark.parametrize("name", LIGHT)
def test_spike_scores_high(name):
    vals = baseline()
    vals[-2] = 100_000.0  # large spike inside the trailing eval window
    score = DETECTORS[name](mod(name)).score(make_series(vals))
    assert score > 0.9, f"{name} spike score {score}"


def test_insufficient_data_raises():
    det = DETECTORS["iqr"](mod("iqr"))
    with pytest.raises(InsufficientData):
        det.score(make_series(baseline(10)))  # < min_train(20) + eval(5)


def test_holt_winters_seasonal():
    pytest.importorskip("statsmodels")
    season = [100 + 10 * math.sin(2 * math.pi * i / 12) + ((i * 13) % 5) * 0.2
              for i in range(96)]
    det = DETECTORS["holt_winters"](mod("holt_winters", season_length=12, k=3))
    clean = det.score(make_series(season))
    spiked = list(season)
    spiked[-2] += 80
    high = det.score(make_series(spiked))
    assert high > 0.9
    assert clean < high - 0.3


def test_prophet_if_available():
    pytest.importorskip("prophet")
    det = DETECTORS["prophet"](mod("prophet"))
    # Prophet is a forecast-band detector. On this short window it auto-disables
    # seasonality, so feed it a gently trending (forecastable) clean baseline
    # rather than the light detectors' raw sine, which trend-only Prophet would
    # mis-extrapolate. A clean continuation must score low; a real spike, high.
    clean = [100 + 0.05 * i + ((i * 29) % 7 - 3) * 0.2 for i in range(120)]
    assert det.score(make_series(clean)) < 0.8
    spiked = list(clean)
    spiked[-2] = 100_000.0
    assert det.score(make_series(spiked)) > 0.9
