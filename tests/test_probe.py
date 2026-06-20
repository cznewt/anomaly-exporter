import textwrap

import pytest
from prometheus_client.parser import text_string_to_metric_families

from anomaly_exporter.app import create_app
from anomaly_exporter.config import load_config


def _samples(body):
    out = {}
    for fam in text_string_to_metric_families(body):
        for s in fam.samples:
            out[(s.name, tuple(sorted(s.labels.items())))] = s.value
    return out


@pytest.fixture
def app(tmp_path, monkeypatch):
    p = tmp_path / "config.yml"
    p.write_text(textwrap.dedent("""
        prometheus: {url: http://prom:9090, timeout: 30s}
        modules:
          cpu:
            detector: iqr
            lookback: 1h
            step: 1m
            eval_points: 5
            min_train_points: 20
            labels: [pod]
            iqr: {k: 1.5}
    """))

    def fake_query_range(self, query, lookback_s, step, timeout=None, now=None):
        base = [[i * 60, 100 + ((i * 37) % 11) * 0.3] for i in range(40)]
        spiked = [list(x) for x in base]
        spiked[-2][1] = 100_000.0
        return [
            {"metric": {"pod": "a"}, "values": spiked},
            {"metric": {"pod": "b"}, "values": base},
        ]

    monkeypatch.setattr(
        "anomaly_exporter.prom.PromClient.query_range", fake_query_range
    )
    return create_app(load_config(p))


def test_probe_success(app):
    r = app.test_client().get("/probe?module=cpu&target=up")
    assert r.status_code == 200
    s = _samples(r.get_data(as_text=True))
    assert s[("anomaly_probe_success", ())] == 1.0
    assert s[("anomaly_series_total", ())] == 2.0
    assert s[("anomaly_series_scored", ())] == 2.0
    assert s[("anomaly_score", (("pod", "a"),))] == 1.0   # spiked series
    assert s[("anomaly_score", (("pod", "b"),))] == 0.0   # clean series


def test_probe_debug_trace(app):
    r = app.test_client().get("/probe?module=cpu&target=up&debug=true")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "detector: iqr" in body
    assert "series returned: 2" in body


def test_unknown_module(app):
    assert app.test_client().get("/probe?module=nope&target=up").status_code == 400


def test_missing_target(app):
    assert app.test_client().get("/probe?module=cpu").status_code == 400


def test_metrics_endpoint(app):
    r = app.test_client().get("/metrics")
    assert r.status_code == 200
    assert "anomaly_exporter_build_info" in r.get_data(as_text=True)


def test_config_endpoint_redacts_token(tmp_path, monkeypatch):
    p = tmp_path / "config.yml"
    p.write_text(textwrap.dedent("""
        prometheus: {url: http://prom:9090, token: supersecret}
        modules:
          m: {detector: iqr, lookback: 1h, step: 1m, iqr: {}}
    """))
    app = create_app(load_config(p))
    body = app.test_client().get("/config").get_data(as_text=True)
    assert "supersecret" not in body
    assert "redacted" in body


def test_healthy(app):
    assert app.test_client().get("/-/healthy").status_code == 200
