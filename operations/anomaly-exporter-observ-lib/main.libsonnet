// observ-viz pack for anomaly-exporter (built on cznewt/observ-viz).
//
//   local p = (import 'main.libsonnet').new({
//     detectorSelectors+: { prophet: 'job="anomaly-mem"' },
//   });
//   p.grafana.dashboard      // a Grafana v2 dashboard (.toSpec() for JSON)
//   p.grafana.elements       // the panels, to reuse in a larger board
//   p.asMonitoringMixin()    // { grafanaDashboards+, prometheusAlerts+ }
//
// Signals are split one file per detector under signals/ (see config.libsonnet).
local pack = import 'libs/common-lib/pack.libsonnet';

{
  new(config={}):
    local cfg = (import 'config.libsonnet') + config;

    // Dashboard row order for the per-detector groups.
    local order = ['prophet', 'holt_winters', 'iqr', 'zscore', 'mean_sigma', 'ewma'];

    // One panel group per detector, from its signals file.
    local groups = [
      {
        title: d,
        width: 12,
        height: 7,
        elements: {
          [d + '_score']: cfg.signals[d].score.asTimeSeries(d + ' score'),
          [d + '_success']: cfg.signals[d].probeSuccess.asStat(d + ' probe success'),
          [d + '_duration']: cfg.signals[d].probeDuration.asTimeSeries(d + ' probe duration'),
        },
      }
      for d in order
    ];

    // All signals, namespaced by detector, for the pack .signals accessor.
    local allSignals = std.foldl(
      function(acc, d) acc + {
        [d + '_' + k]: cfg.signals[d][k]
        for k in std.objectFields(cfg.signals[d])
      },
      order,
      {}
    );

    local thr = '%g' % cfg.scoreThreshold;
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

    local rules = [
      {
        name: 'anomaly-exporter',
        rules: [
          {
            record: 'instance:anomaly_score:max',
            expr: 'max by (instance) (anomaly_score{' + cfg.alertSelector + '})',
          },
        ],
      },
    ];

    pack.build(cfg, allSignals, groups, alerts)
    + { prometheus+: { rules: rules } },
}
