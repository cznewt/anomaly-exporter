import textwrap

import pytest

from anomaly_exporter.config import ConfigError, load_config, parse_duration


def test_parse_duration():
    assert parse_duration("5m") == 300
    assert parse_duration("7d") == 7 * 86400
    assert parse_duration("500ms") == 0.5
    assert parse_duration("1h") == 3600
    assert parse_duration(90) == 90.0
    assert parse_duration("30") == 30.0
    with pytest.raises(ConfigError):
        parse_duration("nonsense")
    with pytest.raises(ConfigError):
        parse_duration(True)  # bool must not be read as 1 second


def _cfg(tmp_path, text):
    p = tmp_path / "config.yml"
    p.write_text(textwrap.dedent(text))
    return load_config(p)


def test_load_minimal(tmp_path):
    cfg = _cfg(tmp_path, """
        prometheus:
          url: http://prom:9090/
        modules:
          m1:
            detector: iqr
            lookback: 1d
            step: 5m
            labels: [pod]
            iqr: {k: 2.0}
    """)
    assert cfg.prometheus.url == "http://prom:9090"  # trailing slash stripped
    m = cfg.modules["m1"]
    assert m.detector == "iqr"
    assert m.lookback == 86400
    assert m.step == "5m"
    assert m.eval_points == 12  # default
    assert m.params == {"k": 2.0}


def test_template_resolution(tmp_path):
    cfg = _cfg(tmp_path, """
        prometheus: {url: http://prom:9090}
        modules:
          t:
            detector: iqr
            query: 'mem{ns="{{target}}"}'
            lookback: 1h
            step: 1m
            iqr: {}
          r:
            detector: iqr
            lookback: 1h
            step: 1m
            iqr: {}
    """)
    assert cfg.modules["t"].resolve_query("prod") == 'mem{ns="prod"}'
    assert cfg.modules["r"].resolve_query("up") == "up"  # no template -> raw target


def test_unknown_detector(tmp_path):
    with pytest.raises(ConfigError):
        _cfg(tmp_path, """
            prometheus: {url: http://prom:9090}
            modules:
              bad: {detector: nope, lookback: 1h, step: 1m}
        """)


def test_missing_url(tmp_path):
    with pytest.raises(ConfigError):
        _cfg(tmp_path, """
            modules:
              m: {detector: iqr, lookback: 1h, step: 1m, iqr: {}}
        """)


def test_missing_required_module_field(tmp_path):
    with pytest.raises(ConfigError):
        _cfg(tmp_path, """
            prometheus: {url: http://prom:9090}
            modules:
              m: {detector: iqr, step: 1m, iqr: {}}
        """)
