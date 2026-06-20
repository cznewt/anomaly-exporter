// Monitoring-mixin output for the monitor-tools render pipeline.
// Override config with: (import 'mixin.libsonnet') + { _config+:: { alertSelector: '...' } }
local lib = import './main.libsonnet';

{
  _config:: {},
  local pack = lib.new($._config),
  grafanaDashboards+:: pack.asMonitoringMixin().grafanaDashboards,
  prometheusAlerts+:: pack.asMonitoringMixin().prometheusAlerts,
  prometheusRules+:: { groups: pack.prometheus.rules },
}
