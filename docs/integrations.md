# Integrations

The exporter uses the multi-target pattern: the thing being probed (the PromQL
query) travels as the `target` parameter, and a relabel step moves it into place
while pointing the scrape at the exporter's address. This page shows how to wire
that up with **Prometheus**, the **Prometheus Operator**, and **Grafana Alloy**.

## Prometheus (scrape config)

One scrape job per module, with the query carried as the target:

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

To also collect the exporter's own operational metrics, add a plain single-target
job against `/metrics`:

```yaml
  - job_name: anomaly-exporter
    metrics_path: /metrics
    static_configs:
      - targets: ['anomaly-exporter:9888']
```

## Prometheus Operator (Probe CRD)

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

## Grafana Alloy

In [Alloy](https://grafana.com/docs/alloy/latest/), build the same multi-target
probe with `discovery.relabel` (to set `__param_target` and the exporter address)
feeding a `prometheus.scrape`:

```alloy
// The PromQL queries to score become the "targets".
discovery.relabel "anomaly_mem" {
  targets = [
    { __address__ = "container_memory_working_set_bytes{namespace=\"production\"}" },
  ]
  rule {
    source_labels = ["__address__"]
    target_label  = "__param_target"
  }
  rule {
    source_labels = ["__param_target"]
    target_label  = "query"
  }
  rule {
    target_label = "__address__"
    replacement  = "anomaly-exporter:9888"
  }
}

prometheus.scrape "anomaly_mem" {
  targets         = discovery.relabel.anomaly_mem.output
  metrics_path    = "/probe"
  params          = { module = ["mem-prophet"] }
  scrape_interval = "5m"
  scrape_timeout  = "2m"
  forward_to      = [prometheus.remote_write.default.receiver]
}
```

Scrape the exporter's own `/metrics` with a second, plain `prometheus.scrape`:

```alloy
prometheus.scrape "anomaly_exporter_self" {
  targets      = [{ __address__ = "anomaly-exporter:9888" }]
  metrics_path = "/metrics"
  forward_to   = [prometheus.remote_write.default.receiver]
}
```

If you discover `Probe` CRDs in-cluster, `prometheus.operator.probes` picks them
up and drives the same `/probe` flow, so the Operator example above works under
Alloy too.

## Timeouts

A probe is synchronous, and the `prophet` and `holt_winters` fits are not free.
The probe budget comes from Prometheus' `X-Prometheus-Scrape-Timeout-Seconds`
header (Alloy sends it from `scrape_timeout` too), minus a small buffer, and is
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
or an unreachable Prometheus), separately from the scores themselves. The
[observ-lib](https://github.com/cznewt/anomaly-exporter/tree/main/operations/anomaly-exporter-observ-lib)
ships starter alerts and a dashboard for this.
