# Configuration

The exporter reads a single YAML file, by default
`/etc/anomaly-exporter/config.yml`. Override the path with `--config.file`, and
reload it at runtime with `POST /-/reload`. The repository
[`config.yml`](https://github.com/cznewt/anomaly-exporter/blob/main/config.yml)
is a complete annotated example.

## Top level

```yaml
prometheus:                       # the Prometheus the exporter QUERIES
  url: http://prometheus:9090
  tenant: ""                      # X-Scope-OrgID header (Mimir/Cortex), optional
  token_file: ""                  # bearer token file, or inline `token:`
  timeout: 60s                    # default per-query HTTP timeout

modules:                          # one named module per detector + parameter set
  <name>:
    detector: <detector>
    ...
```

### `prometheus`

| Field | Default | Meaning |
| :--- | :--- | :--- |
| `url` | _(required)_ | Base URL of the Prometheus-compatible API to query. |
| `tenant` | `""` | Value for the `X-Scope-OrgID` header (Mimir/Cortex multitenancy). |
| `token` | `""` | Bearer token sent as `Authorization: Bearer ...`. |
| `token_file` | `""` | Read the bearer token from this file (takes precedence over `token`). |
| `timeout` | `60s` | Default HTTP timeout for the range query. |

## Modules

Each module names a `detector` and carries that detector's parameters in a block
keyed by the detector name. Common fields apply to every detector:

| Field | Default | Meaning |
| :--- | :--- | :--- |
| `detector` | _(required)_ | One of `prophet`, `holt_winters`, `iqr`, `zscore`, `mean_sigma`, `ewma`. |
| `lookback` | _(required)_ | History to fetch, e.g. `7d`, `12h`, `90m`. |
| `step` | _(required)_ | Query resolution, e.g. `5m` (passed straight to Prometheus). |
| `eval_points` | `12` | Trailing points held out and scored. |
| `min_train_points` | `30` | Skip a series with fewer than this many training points. |
| `labels` | `[]` | Series label keys copied onto the `anomaly_score` gauge. |
| `timeout` | _(none)_ | Optional per-module cap on the probe budget. |
| `query` | _(none)_ | Optional PromQL template with a `{{target}}` placeholder. |
| `<detector>` | `{}` | Detector-specific parameters (see [Detectors](detectors.md)). |

Durations accept `ms`, `s`, `m`, `h`, `d`, `w`, or a bare number of seconds.

> Keep `labels` aligned with the dimensions your query actually returns. If two
> series map to the same label set, they collapse onto one `anomaly_score` line.

## Target: raw query or template

By default the scrape `target` **is** the PromQL query:

```
GET /probe?module=cpu-iqr&target=sum by (pod) (rate(container_cpu_usage_seconds_total[5m]))
```

If a module defines a `query` template, the `target` is a short value spliced into
the `{{target}}` placeholder instead:

```yaml
modules:
  mem-by-namespace:
    detector: iqr
    query: 'container_memory_working_set_bytes{namespace="{{target}}"}'
    lookback: 1d
    step: 5m
    labels: [namespace, pod]
    iqr: { k: 3 }
```

```
GET /probe?module=mem-by-namespace&target=production
```

Templates keep scrape configs short and stop callers from sending arbitrary
PromQL when you would rather pin the query shape.

## Example

```yaml
prometheus:
  url: http://prometheus-operated.monitoring.svc:9090
  timeout: 60s

modules:
  mem-prophet:
    detector: prophet
    lookback: 7d
    step: 5m
    eval_points: 12
    labels: [namespace, pod]
    timeout: 120s
    prophet:
      interval_width: 0.95
      daily_seasonality: true
      weekly_seasonality: auto

  cpu-iqr:
    detector: iqr
    lookback: 1d
    step: 1m
    labels: [pod]
    iqr:
      k: 1.5
```
