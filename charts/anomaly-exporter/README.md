# anomaly-exporter (Helm chart)

Deploys the [anomaly-exporter](https://github.com/cznewt/anomaly-exporter), a
multi-target Prometheus exporter that scores PromQL queries for anomalies.

## Install

The chart is published as an OCI artifact on ghcr:

```bash
# with an inline config file
helm install anomaly-exporter oci://ghcr.io/cznewt/charts/anomaly-exporter \
  --set-file config=./config.yml

# or a specific version
helm install anomaly-exporter oci://ghcr.io/cznewt/charts/anomaly-exporter \
  --version 0.1.0 --set-file config=./config.yml
```

## Configuration

Provide the exporter config one of three ways:

1. Inline under `config:` in your values (rendered into a ConfigMap):
   ```yaml
   config:
     prometheus:
       url: http://prometheus-operated.monitoring.svc:9090
     modules:
       cpu-iqr:
         detector: iqr
         lookback: 1d
         step: 1m
         labels: [pod]
         iqr: { k: 1.5 }
   ```
2. From a file: `--set-file config=./config.yml`.
3. A ConfigMap you manage, with a `config.yml` key: `--set existingConfigMap=my-cm`.

When none is set, the image's baked-in default config is used.

| Value | Default | Description |
| :--- | :--- | :--- |
| `image.repository` | `ghcr.io/cznewt/anomaly-exporter` | Image repository. |
| `image.tag` | chart `appVersion` | Image tag. |
| `replicaCount` | `1` | Number of replicas. |
| `service.type` | `ClusterIP` | Service type. |
| `service.port` | `9888` | Service port. |
| `config` | `{}` | Inline config, or raw file contents via `--set-file`. |
| `existingConfigMap` | `""` | Use an existing ConfigMap (must have a `config.yml` key). |
| `serviceMonitor.enabled` | `false` | Create a ServiceMonitor for the exporter's own `/metrics`. |
| `resources` | `{}` | Pod resource requests/limits. |

## Scraping for scores

The `ServiceMonitor` here scrapes the exporter's own `/metrics` (operational
metrics) only. Anomaly **scores** come from `/probe` and use the multi-target
pattern, so configure a scrape job (or a Prometheus Operator `Probe`) that passes
the query as the target. See
[docs/prometheus.md](https://github.com/cznewt/anomaly-exporter/blob/main/docs/prometheus.md).
