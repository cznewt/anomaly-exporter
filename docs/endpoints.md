# Endpoints and metrics

## HTTP endpoints

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/probe?module=&target=[&debug=true]` | GET | Run a probe and return Prometheus exposition. With `debug=true`, return a plaintext trace instead. |
| `/metrics` | GET | The exporter's own operational metrics. |
| `/config` | GET | The loaded configuration as JSON, bearer token redacted. |
| `/-/reload` | POST | Reload the config file from disk. |
| `/-/healthy`, `/-/ready` | GET | Health check (always `ok` once serving). |
| `/` | GET | Landing page with a probe form. |

## Probe output

A successful `/probe` returns one `anomaly_score` sample per series the query
returned, plus probe metadata:

| Metric | Meaning |
| :--- | :--- |
| `anomaly_score{<labels>}` | Worst trailing point for the series, from `0` to `1`. Labels are the module's `labels`. |
| `anomaly_probe_success` | `1` if the probe ran (query succeeded), else `0`. |
| `anomaly_probe_duration_seconds` | Wall-clock time of the whole probe. |
| `anomaly_series_total` | Series the query returned. |
| `anomaly_series_scored` | Series successfully scored (the rest were skipped for too few points). |

### Debug trace

`debug=true` returns a human-readable trace instead of metrics: the resolved
query, series count, per-series scores, the effective timeout, and totals. Useful
for checking a module by hand before wiring up a scrape job.

```
curl -s 'localhost:9888/probe?module=cpu-iqr&target=up&debug=true'
```

## Exporter metrics (`/metrics`)

These describe the exporter itself, not any probe:

| Metric | Meaning |
| :--- | :--- |
| `anomaly_exporter_build_info{version}` | Build/version info gauge. |
| `anomaly_exporter_probes_total{module,result}` | Probe count by module and `success`/`failure`. |
| `anomaly_exporter_probe_duration_seconds{module}` | Probe duration histogram by module. |

Scrape `/metrics` with an ordinary (single-target) scrape job to monitor the
exporter's own health and probe throughput.
