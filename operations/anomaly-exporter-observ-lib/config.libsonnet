// Default config for the anomaly-exporter observ-viz pack.
// Override any field by passing it to main.new({ ... }).
{
  uid: 'anomaly-exporter',
  dashboardTitle: 'Anomaly Exporter',
  dashboardTags: ['anomaly-exporter'],
  datasource: '${datasource}',

  // Dashboard query selector for the PROBE series (anomaly_score,
  // anomaly_probe_success, ...), driven by the $job template variable.
  selector: 'job=~"$job"',
  varMetric: 'anomaly_probe_success',

  // Static selectors for ALERT expressions (alerts cannot use the $job var):
  alertSelector: '',                            // probe series; scope e.g. 'job=~"anomaly-.+"'
  exporterSelector: 'job="anomaly-exporter"',   // the exporter's own /metrics job

  // Alert tuning.
  scoreThreshold: 0.8,   // anomaly_score above this is an anomaly
  scoreFor: '15m',
  probeFailFor: '15m',
  downFor: '5m',
}
