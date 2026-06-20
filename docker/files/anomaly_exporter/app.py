"""Flask application: the multi-target ``/probe`` endpoint and friends.

``/probe?module=<name>&target=<promql>`` runs the module's range query against the
backing Prometheus, scores each returned series with the module's detector, and
returns the scores as Prometheus exposition synchronously, one fresh registry
per scrape. ``/metrics`` exposes the exporter's *own* operational metrics.
"""
from __future__ import annotations

import logging
import time

from flask import Flask, Response, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from . import __version__
from .config import load_config, redacted
from .detectors import DETECTORS, InsufficientData
from .prom import PromClient

log = logging.getLogger("anomaly-exporter")

# Subtracted from the scrape-timeout header so we answer before Prometheus gives
# up on the scrape.
_TIMEOUT_BUFFER = 0.5


def create_app(config) -> Flask:
    app = Flask(__name__)
    state = {"config": config}

    # The exporter's own operational metrics, served on /metrics (NOT the probe
    # output). A private registry keeps them isolated and lets tests build many
    # apps without duplicate-timeseries errors on the global default registry.
    ops = CollectorRegistry()
    Gauge("anomaly_exporter_build_info", "Build info", ["version"], registry=ops).labels(
        version=__version__
    ).set(1)
    probes_total = Counter(
        "anomaly_exporter_probes_total", "Probes by module and result",
        ["module", "result"], registry=ops,
    )
    probe_duration = Histogram(
        "anomaly_exporter_probe_duration_seconds", "Probe duration by module",
        ["module"], registry=ops,
    )

    def _client() -> PromClient:
        c = state["config"].prometheus
        return PromClient(c.url, tenant=c.tenant, token=c.token, timeout=c.timeout)

    def _effective_timeout(module) -> float:
        """Probe budget: the scrape-timeout header (minus buffer), capped by config."""
        budget = state["config"].prometheus.timeout
        header = request.headers.get("X-Prometheus-Scrape-Timeout-Seconds")
        if header:
            try:
                budget = max(float(header) - _TIMEOUT_BUFFER, 0.1)
            except ValueError:
                pass
        if module.timeout:
            budget = min(budget, module.timeout)
        return budget

    @app.route("/probe")
    def probe():
        module_name = request.args.get("module", "")
        target = request.args.get("target", "")
        debug = request.args.get("debug", "").lower() in ("1", "true", "yes")

        module = state["config"].modules.get(module_name)
        if module is None:
            known = ", ".join(sorted(state["config"].modules))
            return Response(
                f"unknown module {module_name!r}; known modules: {known}\n",
                status=400, mimetype="text/plain",
            )
        if not target:
            return Response("missing 'target' parameter\n", status=400, mimetype="text/plain")

        registry = CollectorRegistry()
        if module.labels:
            score_gauge = Gauge(
                "anomaly_score", "Anomaly score (0..1), worst trailing point per series",
                module.labels, registry=registry,
            )
        else:
            score_gauge = Gauge(
                "anomaly_score", "Anomaly score (0..1), worst trailing point per series",
                registry=registry,
            )
        success_gauge = Gauge("anomaly_probe_success", "1 if the probe succeeded", registry=registry)
        duration_gauge = Gauge("anomaly_probe_duration_seconds", "Probe duration in seconds", registry=registry)
        total_gauge = Gauge("anomaly_series_total", "Series returned by the query", registry=registry)
        scored_gauge = Gauge("anomaly_series_scored", "Series successfully scored", registry=registry)

        query = module.resolve_query(target)
        timeout = _effective_timeout(module)
        detector = DETECTORS[module.detector](module)

        trace = []
        start = time.time()
        deadline = start + timeout
        success, total, scored = 0, 0, 0
        try:
            results = _client().query_range(query, module.lookback, module.step, timeout=timeout)
            total = len(results)
            trace.append(f"query: {query}")
            trace.append(f"series returned: {total}")
            for result in results:
                if time.time() > deadline:
                    trace.append("deadline exceeded; stopping early")
                    break
                metric = result.get("metric", {})
                try:
                    value = detector.score(result["values"])
                except InsufficientData as exc:
                    trace.append(f"skip {metric}: {exc}")
                    continue
                except Exception as exc:  # one bad series must not stop the rest
                    trace.append(f"error {metric}: {exc}")
                    log.warning("score error for %s: %s", metric, exc)
                    continue
                if module.labels:
                    score_gauge.labels(**{k: metric.get(k, "") for k in module.labels}).set(value)
                else:
                    score_gauge.set(value)
                scored += 1
                trace.append(f"scored {metric}: {value:.3f}")
            success = 1
        except Exception as exc:
            trace.append(f"probe failed: {exc}")
            log.warning("probe failed (module=%s target=%s): %s", module_name, target, exc)

        duration = time.time() - start
        success_gauge.set(success)
        duration_gauge.set(duration)
        total_gauge.set(total)
        scored_gauge.set(scored)
        probes_total.labels(module=module_name, result="success" if success else "failure").inc()
        probe_duration.labels(module=module_name).observe(duration)

        if debug:
            body = [
                f"module: {module_name}", f"detector: {module.detector}",
                f"target: {target}", f"timeout: {timeout:.3f}s",
                f"duration: {duration:.3f}s", f"success: {success}",
                f"series_total: {total}", f"series_scored: {scored}", "", *trace,
            ]
            return Response("\n".join(body) + "\n", mimetype="text/plain")
        return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

    @app.route("/metrics")
    def metrics():
        return Response(generate_latest(ops), mimetype=CONTENT_TYPE_LATEST)

    @app.route("/config")
    def show_config():
        return jsonify(redacted(state["config"]))

    @app.route("/-/reload", methods=["POST", "PUT"])
    def reload_config():
        path = state["config"].path
        if not path:
            return Response("config has no file path; cannot reload\n", status=400, mimetype="text/plain")
        try:
            state["config"] = load_config(path)
        except Exception as exc:
            return Response(f"reload failed: {exc}\n", status=500, mimetype="text/plain")
        return Response("reloaded\n", mimetype="text/plain")

    @app.route("/-/healthy")
    @app.route("/-/ready")
    def healthy():
        return Response("ok\n", mimetype="text/plain")

    @app.route("/")
    def index():
        # A small landing page with a probe form for ad-hoc checks.
        options = "".join(
            f'<option value="{name}">{name} ({m.detector})</option>'
            for name, m in sorted(state["config"].modules.items())
        )
        css = (
            "body{font-family:system-ui,sans-serif;margin:2rem;max-width:46rem}"
            "label{display:block;margin:.5rem 0}input,select,button{font:inherit}"
            "code{background:#f3f3f3;padding:.1rem .3rem;border-radius:3px}"
        )
        html = (
            '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            "<title>Anomaly Exporter</title><style>" + css + "</style></head><body>"
            "<h1>Anomaly Exporter</h1>"
            "<p>Multi-target anomaly detection for Prometheus. Scrape "
            "<code>/probe?module=&lt;name&gt;&amp;target=&lt;promql&gt;</code>.</p>"
            '<ul><li><a href="/metrics">Metrics</a> - the exporter\'s own metrics</li>'
            '<li><a href="/config">Config</a> - loaded configuration (token redacted)</li></ul>'
            '<h2>Probe</h2><form action="/probe" method="get">'
            f'<label>Module <select name="module">{options}</select></label>'
            '<label>Target <input name="target" size="60" '
            'placeholder="PromQL query, or a value for a {{target}} template"></label>'
            '<label><input type="checkbox" name="debug" value="true"> debug trace</label>'
            '<button type="submit">Probe</button></form></body></html>'
        )
        return Response(html, mimetype="text/html")

    return app
