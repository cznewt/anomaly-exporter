# anomaly-exporter

An anomaly-detection exporter for Prometheus, built on the
[multi-target exporter pattern](https://prometheus.io/docs/guides/multi-target-exporter/)
— the same shape as [`blackbox_exporter`](https://github.com/prometheus/blackbox_exporter)
and [`snmp_exporter`](https://github.com/prometheus/snmp_exporter).

One exporter, a config file of named **modules**, and a `/probe` endpoint:
Prometheus scrapes `/probe?module=<name>&target=<promql>`, the exporter runs that
range query against your Prometheus on demand, scores each returned series with the
module's detector, and returns the scores — synchronously, per scrape. You pick the
detector and its parameters per module, then alert on the resulting `anomaly_score`
like any other metric.

## How it maps to blackbox / snmp exporter

If you've configured [`blackbox_exporter`](https://github.com/prometheus/blackbox_exporter)
or [`snmp_exporter`](https://github.com/prometheus/snmp_exporter), this is the same
[multi-target pattern](https://prometheus.io/docs/guides/multi-target-exporter/):

| blackbox_exporter | anomaly-exporter |
| :--- | :--- |
| `target` = URL/host to probe | `target` = PromQL query to score |
| `module` → `prober` (http/tcp/dns) | `module` → `detector` (prophet/iqr/zscore/…) |
| prober block (`http:` / `tcp:`) | detector block (`prophet:` / `iqr:` / …) |
| `GET /probe?target=&module=` | `GET /probe?target=&module=` |
| `probe_success`, `probe_duration_seconds` | `anomaly_probe_success`, `anomaly_probe_duration_seconds` |
| `relabel __address__ → __param_target` | identical |
| timeout from the scrape-timeout header | identical |

## How it works

On each `GET /probe?module=<name>&target=<promql>`:

1. Resolve `<name>` to a module from the config; build the query (the raw
   `target`, or the module's `{{target}}` template).
2. `GET /api/v1/query_range` against the backing Prometheus over the module's
   `lookback` at `step` resolution.
3. For each returned series, the module's **detector** holds out the trailing
   `eval_points`, scores each held-out point `0..1`, and reports the worst one.
4. Return `anomaly_score{<labels>}` per series plus probe metadata as Prometheus
   exposition. Nothing is cached: each scrape is fresh, and Prometheus owns the
   cadence (`scrape_interval`).

A series with fewer than `min_train_points + eval_points` samples is skipped; one
bad series never stops the rest.

## Detectors

| `detector` | Method | Key params | Reach for it when |
| :--- | :--- | :--- | :--- |
| `prophet` | Forecast uncertainty band (trend + seasonality) | `interval_width`, `daily_seasonality`, `weekly_seasonality` | The metric has real trend or daily/weekly seasonality. Heaviest. |
| `holt_winters` | Triple exponential smoothing, seasonal forecast band | `season_length`, `trend`, `seasonal`, `k` | Seasonal data, but you want something far lighter than Prophet. |
| `iqr` | Tukey fence `[Q1−k·IQR, Q3+k·IQR]` | `k` | Flat-ish / noisy metrics; robust, training-free. |
| `zscore` | Robust median + MAD ramp | `z_max` | Flat-ish metrics, but you want a smooth severity ramp. |
| `mean_sigma` | Classic mean ± stddev z-score | `z_max` | Clean, roughly-normal baselines; cheapest. |
| `ewma` | EWMA control band | `span`/`alpha`, `k` | Slowly drifting baselines. |

All detectors emit the same `0..1` score, so you can alert on them uniformly.
`iqr`, `zscore`, `mean_sigma` and `ewma` have **no seasonality model** — a strongly
cyclic signal's normal peaks will read as deviations.

## Configuration

Configuration is a YAML file (default `/etc/anomaly-exporter/config.yml`; override
with `--config.file`). See [`config.yml`](config.yml) for a full example.

```yaml
prometheus:                       # the Prometheus we QUERY (the data source)
  url: http://prometheus:9090
  # tenant: ""                    # X-Scope-OrgID header (Mimir/Cortex)
  # token_file: /etc/secrets/tok  # bearer token (or inline `token:`)
  timeout: 60s                    # default per-query HTTP timeout

modules:
  mem-prophet:
    detector: prophet             # which detector
    lookback: 7d                  # history to fetch
    step: 5m                      # query resolution
    eval_points: 12               # trailing points scored (12×5m = 1h)
    min_train_points: 30
    labels: [namespace, pod]      # series labels copied onto anomaly_score{}
    timeout: 120s                 # optional per-module cap
    prophet:                      # detector-specific block (keyed by detector)
      interval_width: 0.95
      daily_seasonality: true
      weekly_seasonality: auto

  cpu-iqr:
    detector: iqr
    lookback: 1d
    step: 1m
    labels: [pod]
    iqr: { k: 1.5 }
```

**Module fields** (common to every detector):

| Field | Default | Description |
| :--- | :--- | :--- |
| `detector` | _(required)_ | One of the detectors above. |
| `lookback` | _(required)_ | History to fetch, e.g. `7d`, `12h`, `90m`. |
| `step` | _(required)_ | Query resolution, e.g. `5m` (passed straight to Prometheus). |
| `eval_points` | `12` | Trailing points held out and scored. |
| `min_train_points` | `30` | Skip a series with fewer than this many training points. |
| `labels` | `[]` | Series label keys copied onto the `anomaly_score` gauge. |
| `timeout` | _(none)_ | Optional per-module cap on the probe budget. |
| `query` | _(none)_ | Optional PromQL template with a `{{target}}` placeholder. |
| `<detector>` | `{}` | Detector-specific params (e.g. an `iqr:` block). |

**`target` is the query** by default. With a `query` template, `target` is a value
spliced into it — so `module: mem-by-namespace`, `target: production` against
`query: 'mem_bytes{namespace="{{target}}"}'` probes that one namespace.

> Keep `labels` aligned with the dimensions your query actually returns, or several
> series will collapse onto the same `anomaly_score` line.

## Endpoints

| Endpoint | Purpose |
| :--- | :--- |
| `GET /probe?module=&target=[&debug=true]` | Run a probe; Prometheus exposition (or a plaintext trace with `debug`). |
| `GET /metrics` | The exporter's **own** metrics (`anomaly_exporter_build_info`, probe counters/histogram). |
| `GET /config` | Loaded config, bearer token redacted. |
| `POST /-/reload` | Reload the config file. |
| `GET /-/healthy` | Health check. |

`/probe` returns: `anomaly_score{<labels>}` (worst trailing point, `0..1`, per
series), `anomaly_probe_success`, `anomaly_probe_duration_seconds`,
`anomaly_series_total`, `anomaly_series_scored`.

## Run

```bash
docker compose up --build
# probe a module + target against a reachable Prometheus (set prometheus.url in config.yml)
curl -s 'localhost:9888/probe?module=cpu-iqr&target=sum by (pod) (rate(container_cpu_usage_seconds_total[5m]))'
# human-readable trace
curl -s 'localhost:9888/probe?module=cpu-iqr&target=...&debug=true'
```

Or directly:

```bash
docker build -t anomaly-exporter ./docker
docker run --rm -p 9888:9888 -v "$PWD/config.yml:/etc/anomaly-exporter/config.yml:ro" anomaly-exporter
```

## Wire up Prometheus

The payoff — one scrape job per module, the query carried as the target:

```yaml
scrape_configs:
  - job_name: anomaly-mem
    metrics_path: /probe
    scrape_interval: 5m
    scrape_timeout: 2m                 # Prophet needs headroom; see Timeouts
    params:
      module: [mem-prophet]
    static_configs:
      - targets:
          - 'container_memory_working_set_bytes{namespace="production"}'
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: query           # keep the query as a label
      - target_label: __address__
        replacement: anomaly-exporter:9888
```

Add one job per module; list several queries under `targets:` to score them all
with the same module.

## Alert on it

The score is just a metric:

```yaml
groups:
  - name: anomaly-exporter
    rules:
      - alert: MetricAnomalyDetected
        expr: anomaly_score > 0.8
        for: 15m
        labels: { severity: warning }
        annotations:
          summary: "Anomaly on {{ $labels.namespace }}/{{ $labels.pod }} (score {{ $value | printf `%.2f` }})"
```

## Timeouts

A probe is synchronous, and `prophet` / `holt_winters` fits are not free. The probe
budget is taken from Prometheus' `X-Prometheus-Scrape-Timeout-Seconds` header
(derived from the job's `scrape_timeout`), minus a small buffer, capped by the
module/global `timeout`. Give model-based modules a generous `scrape_timeout`, and
shard heavy modules across more scrape jobs (or replicas) rather than one giant one.

## Add a detector

Detection is a pluggable registry. To add one: drop a `Detector` subclass in
`docker/files/anomaly_exporter/detectors/mything.py` implementing `point_scores`,
list it in `detectors/__init__.py`, and reference it from config as
`detector: mything` with a `mything:` params block. Keep any heavy imports inside
`point_scores` so config validation and the other detectors stay light.
