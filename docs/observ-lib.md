# Observability library

A Grafana/Jsonnet observability library (monitoring mixin) for the exporter:
Prometheus alerts, a recording rule, and an overview dashboard, built with
[grafonnet](https://github.com/grafana/grafonnet). Source lives in
[`operations/anomaly-exporter-observ-lib`](https://github.com/cznewt/anomaly-exporter/tree/main/operations/anomaly-exporter-observ-lib).

It exposes the standard mixin keys (`prometheusAlerts`, `prometheusRules`,
`grafanaDashboards`), so it drops into the monitor-tools mixin pipeline or any
mimirtool / grizzly workflow.

## What it ships

| Kind | Name | Fires / shows when |
| :--- | :--- | :--- |
| alert | `AnomalyDetected` | `anomaly_score` is above `scoreThreshold` (default `0.8`) for `scoreFor`. |
| alert | `AnomalyProbeFailing` | `anomaly_probe_success == 0` (a probe could not run). |
| alert | `AnomalyExporterProbeErrors` | the exporter records probe failures (`anomaly_exporter_probes_total{result="failure"}`). |
| alert | `AnomalyExporterDown` | the exporter is `up == 0`. |
| rule | `instance:anomaly_score:max` | recording rule: worst score per instance. |
| dashboard | Anomaly Exporter / Overview | score, probe success, probe duration, probe rate. |

## Selectors

There are two, because the exporter's own metrics and its probe output are
scraped by different jobs:

- `selector` (default `job="anomaly-exporter"`) targets the **exporter's own**
  metrics from the single-target `/metrics` scrape (`up`,
  `anomaly_exporter_probes_total`, ...).
- `scoreSelector` (default empty = all) targets the **probe** series
  (`anomaly_score`, `anomaly_probe_success`) produced by the per-module `/probe`
  scrape jobs, which usually carry a different `job` label. Scope it, e.g.
  `job=~"anomaly-.+"`.

Override any `_config` field when importing the mixin:

```jsonnet
local mixin = (import 'mixin.libsonnet') + {
  _config+:: {
    scoreSelector: 'job=~"anomaly-.+"',
    alerts+: { scoreThreshold: 0.9 },
  },
};
```

## Build

Needs `jb`, `jsonnet`, `jsonnetfmt`, and `promtool` on PATH:

```bash
make vendor      # jb install (grafonnet, ...)
make build       # -> prometheus_alerts.yaml, prometheus_rules.yaml, dashboards_out/*.json
make fmt lint test
```

See [Integrations](integrations.md) for how the exporter is scraped in the first
place, and the library
[README](https://github.com/cznewt/anomaly-exporter/blob/main/operations/anomaly-exporter-observ-lib/README.md)
for the file layout.
