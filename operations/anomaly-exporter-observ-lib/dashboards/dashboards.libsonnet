{
  grafanaDashboards+:: {
    local config = $._config,
    'anomaly-exporter-overview.json': (import 'anomaly-exporter-overview.libsonnet')(config),
  },
}
