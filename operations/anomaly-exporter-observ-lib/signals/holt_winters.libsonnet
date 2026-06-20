local signal = import 'libs/common-lib/signal/main.libsonnet';

// Signals for the `holt_winters` detector's probes. anomaly_score has no detector
// label, so cfg.detectorSelectors.holt_winters should scope to the job(s) running
// holt_winters modules (defaults to the global selector).
function(cfg)
  local sel = cfg.detectorSelectors.holt_winters;
  local sig(name, expr, unit='short') =
    signal.new(name, 'prometheus', cfg.datasource, expr, unit).filteringSelector(sel);
  {
    score: sig('Holt-Winters anomaly score', 'anomaly_score{%(queriesSelector)s}', 'percentunit'),
    probeSuccess: sig('Holt-Winters probe success', 'anomaly_probe_success{%(queriesSelector)s}', 'short'),
    probeDuration: sig('Holt-Winters probe duration', 'anomaly_probe_duration_seconds{%(queriesSelector)s}', 's'),
  }
