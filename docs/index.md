# Anomaly Exporter for Prometheus

A multi-target Prometheus exporter that scores PromQL queries for anomalies. It
follows the [multi-target exporter pattern](https://prometheus.io/docs/guides/multi-target-exporter/):
a config file defines named **modules** (a detector plus its parameters), and
Prometheus scrapes `/probe?module=<name>&target=<promql>`. The exporter runs the
range query on demand, scores each returned series, and returns the result
synchronously, one fresh probe per scrape.

## How it works

On each `GET /probe?module=<name>&target=<promql>`:

1. Resolve `<name>` to a module from the config, and build the query (the raw
   `target`, or the module's `{{target}}` template).
2. `GET /api/v1/query_range` against the backing Prometheus over the module's
   `lookback` at `step` resolution.
3. For each returned series, the module's detector scores the trailing
   `eval_points` and reports the worst point as a value from `0` to `1`.
4. Return `anomaly_score{<labels>}` per series plus probe metadata as Prometheus
   exposition.

Nothing is cached. Prometheus owns the cadence through `scrape_interval`, exactly
as it does for other multi-target exporters.

## Sections

- [Configuration](configuration.md): the config file, module fields, and templates.
- [Detectors](detectors.md): the detector catalog, with method, math, parameters,
  and trade-offs for each.
- [Integrations](integrations.md): Prometheus scrape jobs, the Operator `Probe`
  CRD, and Grafana Alloy, plus alerting.
- [Deployment](helm.md): deploy on Kubernetes from the ghcr OCI chart.
- [Observability](observ-lib.md): a grafonnet mixin with alerts, a recording
  rule, and a dashboard.
- [Endpoints](endpoints.md): the HTTP endpoints and exported metrics.

## Install

```bash
# Docker
docker run --rm -p 9888:9888 \
  -v "$PWD/config.yml:/etc/anomaly-exporter/config.yml:ro" \
  ghcr.io/cznewt/anomaly-exporter:latest

# Helm (OCI artifact on ghcr)
helm install anomaly-exporter oci://ghcr.io/cznewt/charts/anomaly-exporter \
  --set-file config=./config.yml
```
