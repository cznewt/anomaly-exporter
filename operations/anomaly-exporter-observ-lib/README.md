# anomaly-exporter-observ-lib

An [observ-viz](https://github.com/cznewt/observ-viz) pack for
[anomaly-exporter](https://github.com/cznewt/anomaly-exporter): a Grafana v2
dashboard plus Prometheus alerts, built from a small set of signals. It mirrors
the layout of observ-viz's other packs (e.g. `memcached-observ-lib`).

> Built on observ-viz; not compiled in this repo (no jsonnet toolchain here).
> Run `just observ-lib-build` (from the repo root) to `jb install` and render,
> which will shake out any issues.

## Files

```
config.libsonnet     default config (uid, selectors, thresholds) + imports the signals
signals/*.libsonnet  one file per detector (prophet, holt_winters, iqr, zscore,
                     mean_sigma, ewma); windows-observ-lib style
main.libsonnet       new(config) -> pack.build(signals, groups, alerts)
mixin.libsonnet      asMonitoringMixin(): grafanaDashboards + prometheusAlerts
lib/*.jsonnet        render entrypoints (dashboards JSON, alerts YAML)
tests/tests.yaml     promtool unit tests for the alerts
jsonnetfile.json     depends on cznewt/observ-viz
```

The dashboard has one row per detector, each built from its `signals/<detector>.libsonnet`.

## Use

```jsonnet
local p = (import 'main.libsonnet').new({
  alertSelector: 'job=~"anomaly-.+"',   // scope alerts to your probe jobs
  scoreThreshold: 0.9,
});

p.grafana.dashboard      // a Grafana v2 dashboard (.toSpec() for JSON)
p.grafana.elements       // the panels, to reuse in a larger board
p.asMonitoringMixin()    // { grafanaDashboards+::, prometheusAlerts+:: }
```

## Build

Needs `jb`, `jsonnet`, `jsonnetfmt`, and `promtool` on PATH. From the repo root:

```bash
just observ-lib-build   # jb install + render dashboards_out/*.json + prometheus_alerts.yaml
just observ-lib-test    # promtool-test the rendered alerts
just observ-lib-fmt     # jsonnetfmt
```

## Selectors

Three selectors, because the exporter's own metrics and its probe output are
scraped by different jobs:

- `selector` (default `job=~"$job"`) drives the **dashboard** through the `$job`
  template variable, over the probe series (`anomaly_score`, ...).
- `alertSelector` (default empty = all) is the **static** selector for alert
  expressions on the probe series (alerts cannot use `$job`).
- `exporterSelector` (default `job="anomaly-exporter"`) is for alerts on the
  exporter's own `/metrics` (`up`, `anomaly_exporter_probes_total`).
- `detectorSelectors` maps each detector to the selector for its dashboard row.
  `anomaly_score` has no detector label, so scope each to the job(s) running that
  detector's modules (e.g. `{ prophet: 'job="anomaly-mem"' }`); defaults to the
  global `selector`.

See the [Observability docs](https://cznewt.github.io/anomaly-exporter/observ-lib/)
and [Integrations](https://github.com/cznewt/anomaly-exporter/blob/main/docs/integrations.md).
