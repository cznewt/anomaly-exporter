{
  prometheusAlerts+:: {
    local config = $._config,
    groups+: [
      {
        name: 'anomaly-exporter',
        rules: [
          {
            alert: 'AnomalyDetected',
            // Fires per anomalous series. Tune scoreThreshold / scoreFor in
            // config, and scoreSelector to scope to your probe job(s).
            expr: 'anomaly_score{%(sel)s} > %(threshold)s' % {
              sel: config.scoreSelector,
              threshold: config.alerts.scoreThreshold,
            },
            'for': config.alerts.scoreFor,
            labels: { severity: 'warning' },
            annotations: {
              summary: 'anomaly-exporter detected a metric anomaly.',
              description: 'anomaly_score is {{ $value | printf "%.2f" }} on {{ $labels.instance }} (threshold ' + std.toString(config.alerts.scoreThreshold) + ').',
            },
          },
          {
            alert: 'AnomalyProbeFailing',
            expr: 'anomaly_probe_success{%(sel)s} == 0' % { sel: config.scoreSelector },
            'for': config.alerts.probeFailFor,
            labels: { severity: 'warning' },
            annotations: {
              summary: 'An anomaly-exporter probe is failing.',
              description: 'anomaly_probe_success is 0 on {{ $labels.instance }} (the query failed or Prometheus was unreachable).',
            },
          },
          {
            alert: 'AnomalyExporterProbeErrors',
            expr: 'increase(anomaly_exporter_probes_total{%(sel)s, result="failure"}[15m]) > 0' % { sel: config.selector },
            'for': config.alerts.probeErrorFor,
            labels: { severity: 'warning' },
            annotations: {
              summary: 'anomaly-exporter is recording probe failures.',
              description: 'Module {{ $labels.module }} probes are failing on {{ $labels.instance }}.',
            },
          },
          {
            alert: 'AnomalyExporterDown',
            expr: 'up{%(sel)s} == 0' % { sel: config.selector },
            'for': config.alerts.downFor,
            labels: { severity: 'critical' },
            annotations: {
              summary: 'anomaly-exporter is down.',
              description: '{{ $labels.instance }} has been unreachable for more than ' + config.alerts.downFor + '.',
            },
          },
        ],
      },
    ],
  },
}
