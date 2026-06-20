local signal = import 'libs/common-lib/signal/main.libsonnet';

// Signals for the `mean_sigma` detector's probes. anomaly_score has no detector
// label, so cfg.detectorSelectors.mean_sigma should scope to the job(s) running
// mean_sigma modules (defaults to the global selector).
function(cfg)
  local sel = cfg.detectorSelectors.mean_sigma;
  local sig(name, expr, unit='short') =
    signal.new(name, 'prometheus', cfg.datasource, expr, unit).filteringSelector(sel);
  {
    score: sig('Mean/sigma anomaly score', 'anomaly_score{%(queriesSelector)s}', 'percentunit'),
    probeSuccess: sig('Mean/sigma probe success', 'anomaly_probe_success{%(queriesSelector)s}', 'short'),
    probeDuration: sig('Mean/sigma probe duration', 'anomaly_probe_duration_seconds{%(queriesSelector)s}', 's'),
  }
