local signal = import 'libs/common-lib/signal/main.libsonnet';

// Signals for the `ewma` detector's probes. anomaly_score has no detector label,
// so cfg.detectorSelectors.ewma should scope to the job(s) running ewma modules
// (defaults to the global selector).
function(cfg)
  local sel = cfg.detectorSelectors.ewma;
  local sig(name, expr, unit='short') =
    signal.new(name, 'prometheus', cfg.datasource, expr, unit).filteringSelector(sel);
  {
    score: sig('EWMA anomaly score', 'anomaly_score{%(queriesSelector)s}', 'percentunit'),
    probeSuccess: sig('EWMA probe success', 'anomaly_probe_success{%(queriesSelector)s}', 'short'),
    probeDuration: sig('EWMA probe duration', 'anomaly_probe_duration_seconds{%(queriesSelector)s}', 's'),
  }
