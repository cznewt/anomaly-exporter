// observ-viz pack for anomaly-exporter (built on cznewt/observ-viz).
//
//   local p = (import 'main.libsonnet').new({ alertSelector: 'job=~"anomaly-.+"' });
//   p.grafana.dashboard        // a Grafana v2 dashboard (.toSpec() for JSON)
//   p.grafana.elements         // reuse panels in a larger board
//   p.asMonitoringMixin()      // { grafanaDashboards+, prometheusAlerts+ }
//
// See config.libsonnet for the tunable fields.
local pack = import 'libs/common-lib/pack.libsonnet';
local signal = import 'libs/common-lib/signal/main.libsonnet';

{
  new(config={}):
    local cfg = (import 'config.libsonnet') + config;

    local sig(name, expr, unit='short') =
      signal.new(name, 'prometheus', cfg.datasource, expr, unit).filteringSelector(cfg.selector);

    local signals = {
      score: sig('Anomaly score', 'anomaly_score{%(queriesSelector)s}', 'percentunit'),
      probeSuccess: sig('Probe success', 'anomaly_probe_success{%(queriesSelector)s}', 'short'),
      probeDuration: sig('Probe duration', 'anomaly_probe_duration_seconds{%(queriesSelector)s}', 's'),
      seriesScored: sig('Series scored', 'anomaly_series_scored{%(queriesSelector)s}', 'short'),
      seriesTotal: sig('Series total', 'anomaly_series_total{%(queriesSelector)s}', 'short'),
    };

    local thr = std.toString(cfg.scoreThreshold);
    local alerts = [
      {
        name: 'anomaly-exporter',
        rules: [
          {
            alert: 'AnomalyDetected',
            expr: 'anomaly_score{' + cfg.alertSelector + '} > ' + thr,
            'for': cfg.scoreFor,
            labels: { severity: 'warning' },
            annotations: {
              summary: 'anomaly-exporter detected a metric anomaly.',
              description: 'anomaly_score is {{ $value | printf "%.2f" }} on {{ $labels.instance }} (threshold ' + thr + ').',
            },
          },
          {
            alert: 'AnomalyProbeFailing',
            expr: 'anomaly_probe_success{' + cfg.alertSelector + '} == 0',
            'for': cfg.probeFailFor,
            labels: { severity: 'warning' },
            annotations: {
              summary: 'An anomaly-exporter probe is failing.',
              description: 'anomaly_probe_success is 0 on {{ $labels.instance }} (the query failed or Prometheus was unreachable).',
            },
          },
          {
            alert: 'AnomalyExporterProbeErrors',
            expr: 'increase(anomaly_exporter_probes_total{' + cfg.exporterSelector + ', result="failure"}[15m]) > 0',
            'for': cfg.probeFailFor,
            labels: { severity: 'warning' },
            annotations: {
              summary: 'anomaly-exporter is recording probe failures.',
              description: 'Module {{ $labels.module }} probes are failing on {{ $labels.instance }}.',
            },
          },
          {
            alert: 'AnomalyExporterDown',
            expr: 'up{' + cfg.exporterSelector + '} == 0',
            'for': cfg.downFor,
            labels: { severity: 'critical' },
            annotations: {
              summary: 'anomaly-exporter is down.',
              description: '{{ $labels.instance }} has been unreachable for more than ' + cfg.downFor + '.',
            },
          },
        ],
      },
    ];

    pack.build(cfg, signals, [
      {
        title: 'Anomaly scores',
        width: 12,
        height: 7,
        elements: {
          score: signals.score.asTimeSeries('Anomaly score'),
          probeSuccess: signals.probeSuccess.asStat('Probe success'),
        },
      },
      {
        title: 'Probe health',
        width: 12,
        height: 7,
        elements: {
          probeDuration: signals.probeDuration.asTimeSeries('Probe duration'),
          seriesScored: signals.seriesScored.asTimeSeries('Series scored'),
          seriesTotal: signals.seriesTotal.asTimeSeries('Series total'),
        },
      },
    ], alerts),
}
