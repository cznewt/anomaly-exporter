# anomaly-exporter-observ-lib

A Grafana/Jsonnet observability library (monitoring mixin) for
[anomaly-exporter](https://github.com/cznewt/anomaly-exporter): starter Prometheus
alerts, a recording rule, and an overview dashboard built with
[grafonnet](https://github.com/grafana/grafonnet).

> Scaffold. The structure and a baseline of alerts/dashboard are here; extend the
> signals, panels, and thresholds to taste. It has not been compiled in this repo
> (no jsonnet toolchain here) -- run `make fmt build` to format, render, and shake
> out any issues.

## Layout

```
config.libsonnet      tunable selectors, labels, thresholds (_config)
mixin.libsonnet       merges alerts + rules + dashboards + config
alerts/alerts.libsonnet   prometheusAlerts (AnomalyDetected, probe failing, ...)
rules/rules.libsonnet     prometheusRules (recording rules)
dashboards/           grafanaDashboards (overview)
lib/*.jsonnet         render entrypoints used by the Makefile
tests/tests.yaml      promtool unit tests for the alerts
```

## Build

Needs `jb` (jsonnet-bundler), `jsonnet`, `jsonnetfmt`, and `promtool` on PATH.

```bash
make vendor      # jb install (grafonnet, etc.)
make build       # -> prometheus_alerts.yaml, prometheus_rules.yaml, dashboards_out/*.json
make fmt lint test
```

## Configure

Override anything under `_config` (see `config.libsonnet`). Note the two
selectors:

- `selector` (default `job="anomaly-exporter"`) targets the exporter's **own**
  metrics from the single-target `/metrics` scrape (`up`,
  `anomaly_exporter_probes_total`, ...).
- `scoreSelector` (default empty = all) targets the **probe** series
  (`anomaly_score`, `anomaly_probe_success`) that the per-module `/probe` scrape
  jobs produce, which usually carry a different `job` label.

```jsonnet
local mixin = (import 'mixin.libsonnet') + {
  _config+:: {
    scoreSelector: 'job=~"anomaly-.+"',
    alerts+: { scoreThreshold: 0.9 },
  },
};
```

## Consume

The mixin exposes the standard `prometheusAlerts`, `prometheusRules`, and
`grafanaDashboards` keys, so it drops into the monitor-tools mixin pipeline or any
mimirtool / grizzly workflow. See
[docs/integrations.md](https://github.com/cznewt/anomaly-exporter/blob/main/docs/integrations.md)
for how the exporter is scraped in the first place.
