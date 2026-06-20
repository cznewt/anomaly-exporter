// Default config for the anomaly-exporter observ-viz pack.
// Override any field by passing it to main.new({ ... }).
{
  local this = self,

  uid: 'anomaly-exporter',
  dashboardTitle: 'Anomaly Exporter',
  dashboardTags: ['anomaly-exporter'],
  datasource: '${datasource}',

  // Dashboard query selector for the PROBE series, driven by the $job variable.
  selector: 'job=~"$job"',
  varMetric: 'anomaly_probe_success',

  // Static selectors for ALERT expressions (alerts cannot use the $job var).
  alertSelector: '',                            // probe series; scope e.g. 'job=~"anomaly-.+"'
  exporterSelector: 'job="anomaly-exporter"',   // the exporter's own /metrics job

  // Alert tuning.
  scoreThreshold: 0.8,
  scoreFor: '15m',
  probeFailFor: '15m',
  downFor: '5m',

  // Per-detector scoping. anomaly_score carries the module's labels but NOT a
  // detector label, so scope each detector to the scrape job(s) running its
  // modules, e.g. 'job=~"anomaly-.*prophet.*"'. Defaults to the global selector.
  detectorSelectors: {
    prophet: this.selector,
    holt_winters: this.selector,
    iqr: this.selector,
    zscore: this.selector,
    mean_sigma: this.selector,
    ewma: this.selector,
  },

  // Per-detector signals, one file each (windows-observ-lib style).
  signals: {
    prophet: (import './signals/prophet.libsonnet')(this),
    holt_winters: (import './signals/holt_winters.libsonnet')(this),
    iqr: (import './signals/iqr.libsonnet')(this),
    zscore: (import './signals/zscore.libsonnet')(this),
    mean_sigma: (import './signals/mean_sigma.libsonnet')(this),
    ewma: (import './signals/ewma.libsonnet')(this),
  },
}
