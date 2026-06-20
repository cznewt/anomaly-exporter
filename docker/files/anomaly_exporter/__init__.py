"""Multi-target anomaly exporter for Prometheus.

A single exporter that runs PromQL range queries on demand and scores them for
anomalies with a config-selected detector, following Prometheus' multi-target
exporter pattern: ``GET /probe?module=<name>&target=<promql>``.
"""
import os

__version__ = os.environ.get("ANOMALY_EXPORTER_VERSION", "0.1.0")
