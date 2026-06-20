# Build the anomaly-exporter observability library.
# Tools expected on PATH: jb (jsonnet-bundler), jsonnet, jsonnetfmt, promtool.

DASHBOARDS_OUT = dashboards_out

.PHONY: all
all: vendor build

vendor: jsonnetfile.json
	jb install

.PHONY: build
build: prometheus_alerts.yaml prometheus_rules.yaml dashboards

prometheus_alerts.yaml: vendor mixin.libsonnet config.libsonnet alerts/*.libsonnet lib/alerts.jsonnet
	jsonnet -J vendor -S lib/alerts.jsonnet > $@

prometheus_rules.yaml: vendor mixin.libsonnet config.libsonnet rules/*.libsonnet lib/rules.jsonnet
	jsonnet -J vendor -S lib/rules.jsonnet > $@

.PHONY: dashboards
dashboards: vendor mixin.libsonnet config.libsonnet dashboards/*.libsonnet lib/dashboards.jsonnet
	@mkdir -p $(DASHBOARDS_OUT)
	jsonnet -J vendor -m $(DASHBOARDS_OUT) lib/dashboards.jsonnet

.PHONY: fmt
fmt:
	@find . -name vendor -prune -o \( -name '*.libsonnet' -o -name '*.jsonnet' \) -print \
		| xargs -n 1 jsonnetfmt -i

.PHONY: lint
lint: prometheus_alerts.yaml prometheus_rules.yaml
	promtool check rules prometheus_alerts.yaml prometheus_rules.yaml

.PHONY: test
test: prometheus_alerts.yaml prometheus_rules.yaml
	promtool test rules tests/*.yaml

.PHONY: clean
clean:
	rm -rf vendor $(DASHBOARDS_OUT) prometheus_alerts.yaml prometheus_rules.yaml
