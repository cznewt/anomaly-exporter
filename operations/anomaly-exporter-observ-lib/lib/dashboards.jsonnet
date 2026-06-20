// Manifest each dashboard to a JSON string so `jsonnet -m` writes one file per board.
local dashboards = (import '../mixin.libsonnet').grafanaDashboards;

{
  [name]: std.manifestJsonEx(dashboards[name], '  ')
  for name in std.objectFields(dashboards)
}
