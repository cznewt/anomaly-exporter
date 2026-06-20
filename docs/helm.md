# Deployment

A Helm chart deploys the exporter on Kubernetes. It is published as an OCI
artifact on ghcr, and the source lives in
[`operations/anomaly-exporter-helm-chart`](https://github.com/cznewt/anomaly-exporter/tree/main/operations/anomaly-exporter-helm-chart).

## Install

```bash
helm install anomaly-exporter oci://ghcr.io/cznewt/charts/anomaly-exporter \
  --set-file config=./config.yml
```

Pin a version with `--version <x.y.z>`. The chart's `appVersion` tracks the image
tag, and `image.tag` defaults to it.

## Providing the config

Give the exporter its `config.yml` one of three ways:

1. **Inline** under `config:` in your values (rendered into a ConfigMap):
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
2. **From a file**: `--set-file config=./config.yml`.
3. **An existing ConfigMap** you manage (must have a `config.yml` key):
   `--set existingConfigMap=my-cm`.

With none set, the image's baked-in default config is used.

## Key values

| Value | Default | Description |
| :--- | :--- | :--- |
| `image.repository` | `ghcr.io/cznewt/anomaly-exporter` | Image repository. |
| `image.tag` | chart `appVersion` | Image tag. |
| `replicaCount` | `1` | Number of replicas. |
| `service.type` / `service.port` | `ClusterIP` / `9888` | Service exposure. |
| `config` | `{}` | Inline config, or raw file via `--set-file`. |
| `existingConfigMap` | `""` | Use an existing ConfigMap (`config.yml` key). |
| `serviceMonitor.enabled` | `false` | ServiceMonitor for the exporter's own `/metrics`. |
| `resources` | `{}` | Pod resource requests/limits. |

See the chart
[README](https://github.com/cznewt/anomaly-exporter/blob/main/operations/anomaly-exporter-helm-chart/README.md)
for the full list.

## Scraping for scores

The optional `ServiceMonitor` scrapes only the exporter's own `/metrics`
(operational metrics). Anomaly **scores** come from `/probe` and use the
multi-target pattern, so configure a scrape job or `Probe` CRD as described in
[Integrations](integrations.md). Pair the chart with the
[observability library](observ-lib.md) for ready-made alerts and a dashboard.
