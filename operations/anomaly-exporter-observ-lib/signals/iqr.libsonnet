local signal = import 'libs/common-lib/signal/main.libsonnet';

// Signals for the `iqr` detector's probes. anomaly_score has no detector label,
// so cfg.detectorSelectors.iqr should scope to the job(s) running iqr modules
// (defaults to the global selector).
function(cfg)
  local sel = cfg.detectorSelectors.iqr;
  local sig(name, expr, unit='short') =
    signal.new(name, 'prometheus', cfg.datasource, expr, unit).filteringSelector(sel);
  {
    score: sig('IQR anomaly score', 'anomaly_score{%(queriesSelector)s}', 'percentunit'),
    probeSuccess: sig('IQR probe success', 'anomaly_probe_success{%(queriesSelector)s}', 'short'),
    probeDuration: sig('IQR probe duration', 'anomaly_probe_duration_seconds{%(queriesSelector)s}', 's'),
  }
