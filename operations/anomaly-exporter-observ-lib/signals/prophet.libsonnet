local signal = import 'libs/common-lib/signal/main.libsonnet';

// Signals for the `prophet` detector's probes. anomaly_score has no detector
// label, so cfg.detectorSelectors.prophet should scope to the job(s) running
// prophet modules (defaults to the global selector).
function(cfg)
  local sel = cfg.detectorSelectors.prophet;
  local sig(name, expr, unit='short') =
    signal.new(name, 'prometheus', cfg.datasource, expr, unit).filteringSelector(sel);
  {
    score: sig('Prophet anomaly score', 'anomaly_score{%(queriesSelector)s}', 'percentunit'),
    probeSuccess: sig('Prophet probe success', 'anomaly_probe_success{%(queriesSelector)s}', 'short'),
    probeDuration: sig('Prophet probe duration', 'anomaly_probe_duration_seconds{%(queriesSelector)s}', 's'),
  }
