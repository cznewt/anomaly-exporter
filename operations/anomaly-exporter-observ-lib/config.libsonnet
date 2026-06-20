{
  _config+:: {
    // Selector for the exporter's OWN metrics (the single-target /metrics job):
    // up, anomaly_exporter_build_info, anomaly_exporter_probes_total, ...
    selector: 'job="anomaly-exporter"',

    // Selector for the PROBE series (anomaly_score, anomaly_probe_success, ...),
    // which come from the per-module /probe scrape jobs and so usually carry a
    // different job label. Leave empty to match all, or scope it,
    // e.g. 'job=~"anomaly-.+"'.
    scoreSelector: '',

    // Label conventions.
    instanceLabel: 'instance',

    // Grafana.
    datasourceName: 'default',
    dashboardTags: ['anomaly-exporter'],
    dashboardUids: {
      overview: 'anomaly-exporter-overview',
    },

    // Alert tuning.
    alerts: {
      scoreThreshold: 0.8,   // anomaly_score above this is an anomaly
      scoreFor: '15m',
      probeFailFor: '15m',
      probeErrorFor: '15m',
      downFor: '5m',
    },
  },
}
