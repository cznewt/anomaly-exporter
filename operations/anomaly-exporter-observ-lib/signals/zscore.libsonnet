local signal = import 'libs/common-lib/signal/main.libsonnet';

// Signals for the `zscore` detector's probes. anomaly_score has no detector
// label, so cfg.detectorSelectors.zscore should scope to the job(s) running
// zscore modules (defaults to the global selector).
function(cfg)
  local sel = cfg.detectorSelectors.zscore;
  local sig(name, expr, unit='short') =
    signal.new(name, 'prometheus', cfg.datasource, expr, unit).filteringSelector(sel);
  {
    score: sig('Z-score anomaly score', 'anomaly_score{%(queriesSelector)s}', 'percentunit'),
    probeSuccess: sig('Z-score probe success', 'anomaly_probe_success{%(queriesSelector)s}', 'short'),
    probeDuration: sig('Z-score probe duration', 'anomaly_probe_duration_seconds{%(queriesSelector)s}', 's'),
  }
