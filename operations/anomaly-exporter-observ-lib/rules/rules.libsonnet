{
  prometheusRules+:: {
    local config = $._config,
    groups+: [
      {
        name: 'anomaly-exporter.rules',
        rules: [
          {
            // Worst current anomaly score per exporter instance.
            record: 'instance:anomaly_score:max',
            expr: 'max by (%(instanceLabel)s) (anomaly_score{%(sel)s})' % {
              instanceLabel: config.instanceLabel,
              sel: config.scoreSelector,
            },
          },
        ],
      },
    ],
  },
}
