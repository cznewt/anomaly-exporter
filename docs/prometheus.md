# Wiring up Prometheus

The exporter uses the multi-target pattern: the thing being probed (the PromQL
query) travels as the `target` parameter, and a relabel step moves it into place
while pointing the scrape at the exporter's address.

## Scrape job per module

```yaml
scrape_configs:
  - job_name: anomaly-mem
    metrics_path: /probe
    scrape_interval: 5m
    scrape_timeout: 2m                 # model detectors need headroom (see Timeouts)
    params:
      module: [mem-prophet]
    static_configs:
      - targets:
          - 'container_memory_working_set_bytes{namespace="production"}'
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: query            # keep the query as a label
      - target_label: __address__
        replacement: anomaly-exporter:9888
```

List several queries under `targets:` to score them all with the same module, and
add one job per module. The `query` relabel is optional but handy: it keeps the
probed PromQL visible as a label on the resulting series.

## Prometheus Operator Probe CRD

If you run the Prometheus Operator, the `Probe` resource expresses the same
pattern declaratively:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: Probe
metadata:
  name: anomaly-mem
spec:
  interval: 5m
  scrapeTimeout: 2m
  module: mem-prophet
  prober:
    url: anomaly-exporter:9888
    path: /probe
  targets:
    staticConfig:
      static:
        - 'container_memory_working_set_bytes{namespace="production"}'
```

## Timeouts

A probe is synchronous, and the `prophet` and `holt_winters` fits are not free.
The probe budget comes from Prometheus' `X-Prometheus-Scrape-Timeout-Seconds`
header (derived from the job's `scrape_timeout`), minus a small buffer, and is
then capped by the module or global `timeout`. Give model-based modules a generous
`scrape_timeout`, and shard heavy modules across more scrape jobs or replicas
rather than one giant job.

## Alerting

The score is an ordinary metric, so alert on it directly:

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

Use `anomaly_probe_success == 0` to alert on probes that fail to run (a bad query
or an unreachable Prometheus), separately from the scores themselves.
