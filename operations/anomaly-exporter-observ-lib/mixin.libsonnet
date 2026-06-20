// Monitoring-mixin output for the monitor-tools render pipeline.
// Override config with: (import 'mixin.libsonnet') + { _config+:: { alertSelector: '...' } }
local lib = import './main.libsonnet';

{
  _config:: {},
  _pack:: lib.new(self._config),
  grafanaDashboards+:: self._pack.asMonitoringMixin().grafanaDashboards,
  prometheusAlerts+:: self._pack.asMonitoringMixin().prometheusAlerts,
  prometheusRules+:: { groups: self._pack.prometheus.recordingRules },
}
