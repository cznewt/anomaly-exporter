local g = import 'github.com/grafana/grafonnet/gen/grafonnet-latest/main.libsonnet';

local prometheus = g.query.prometheus;
local timeSeries = g.panel.timeSeries;
local stat = g.panel.stat;
local var = g.dashboard.variable;

// Starting-point overview dashboard. Run `make fmt dashboards` to format and
// render; extend with rows/panels as needed.
function(config)
  local datasource =
    var.datasource.new('datasource', 'prometheus')
    + var.datasource.generalOptions.withLabel('Data source');

  local target(expr, legend) =
    prometheus.new('${datasource}', expr)
    + prometheus.withLegendFormat(legend);

  local scorePanel =
    timeSeries.new('Anomaly score')
    + timeSeries.standardOptions.withMin(0)
    + timeSeries.standardOptions.withMax(1)
    + timeSeries.queryOptions.withTargets([
      target('anomaly_score{%(s)s}' % { s: config.scoreSelector }, '{{instance}}'),
    ]);

  local successPanel =
    stat.new('Probe success (min)')
    + stat.queryOptions.withTargets([
      target('min(anomaly_probe_success{%(s)s})' % { s: config.scoreSelector }, 'success'),
    ]);

  local durationPanel =
    timeSeries.new('Probe duration')
    + timeSeries.standardOptions.withUnit('s')
    + timeSeries.queryOptions.withTargets([
      target('anomaly_probe_duration_seconds{%(s)s}' % { s: config.scoreSelector }, '{{instance}}'),
    ]);

  local probesPanel =
    timeSeries.new('Probes per second')
    + timeSeries.queryOptions.withTargets([
      target(
        'sum by (module, result) (rate(anomaly_exporter_probes_total{%(s)s}[$__rate_interval]))' % { s: config.selector },
        '{{module}} {{result}}'
      ),
    ]);

  g.dashboard.new('Anomaly Exporter / Overview')
  + g.dashboard.withUid(config.dashboardUids.overview)
  + g.dashboard.withTags(config.dashboardTags)
  + g.dashboard.withRefresh('1m')
  + g.dashboard.withVariables([datasource])
  + g.dashboard.withPanels(
    g.util.grid.makeGrid(
      [scorePanel, successPanel, durationPanel, probesPanel],
      panelWidth=12,
      panelHeight=8,
    )
  )
