"""Detector registry.

Each detector module defines a :class:`~.base.Detector` subclass with a unique
``.name``. Adding a method is a one-file change: drop in ``mything.py`` and list
the class below. Heavy third-party imports (prophet, statsmodels) live *inside*
each detector's ``point_scores``, so importing this registry (to list or
construct detectors, or to validate config) never pulls them in. Only actually
scoring a series does.
"""
from .base import Detector, InsufficientData
from .ewma import EwmaDetector
from .holt_winters import HoltWintersDetector
from .iqr import IqrDetector
from .mean_sigma import MeanSigmaDetector
from .prophet import ProphetDetector
from .zscore import ZScoreDetector

DETECTORS = {
    cls.name: cls
    for cls in (
        ProphetDetector,
        IqrDetector,
        ZScoreDetector,
        MeanSigmaDetector,
        EwmaDetector,
        HoltWintersDetector,
    )
}

__all__ = ["DETECTORS", "Detector", "InsufficientData"]
