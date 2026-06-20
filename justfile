#!/usr/bin/env just --justfile

# Image + chart coordinates (override on the CLI, e.g. `just TAG=dev publish`)
REGISTRY := "ghcr.io"
IMAGE := "cznewt/anomaly-exporter"
TAG := `cat VERSION`
CHART := "operations/anomaly-exporter-helm-chart"
CHARTS_NAMESPACE := "cznewt/charts"
OBSERV_LIB := "operations/anomaly-exporter-observ-lib"

default:
  just --list

# --- Local dev ---

# Build the local dev image via compose
build:
    docker compose build

# Run the exporter (mounts ./config.yml)
run:
    docker compose up

# Probe a module + target against a running exporter
probe MODULE TARGET:
    curl -s "localhost:9888/probe?module={{MODULE}}&target={{TARGET}}"

# Same, with the human-readable debug trace
debug MODULE TARGET:
    curl -s "localhost:9888/probe?module={{MODULE}}&target={{TARGET}}&debug=true"

# Run the test suite (expects a .venv with the deps installed)
test:
    .venv/bin/pytest -q

# Serve the docs locally with live reload (needs: pip install mkdocs-material)
docs-serve:
    mkdocs serve

# Build the docs site (strict; mirrors the Pages workflow)
docs-build:
    mkdocs build --strict

# --- Container registry (ghcr) ---

# Log in to ghcr. Set GHCR_USER + GHCR_TOKEN (a GitHub PAT with write:packages).
login:
    echo "${GHCR_TOKEN:?set GHCR_TOKEN to a GitHub PAT with write:packages}" | docker login {{REGISTRY}} -u "${GHCR_USER:?set GHCR_USER to your GitHub username}" --password-stdin

# Build the image, tagged :<VERSION> and :latest
image:
    docker build -t {{REGISTRY}}/{{IMAGE}}:{{TAG}} -t {{REGISTRY}}/{{IMAGE}}:latest ./docker

# Push both tags to ghcr (run `just login` first)
push:
    docker push {{REGISTRY}}/{{IMAGE}}:{{TAG}}
    docker push {{REGISTRY}}/{{IMAGE}}:latest

# Build and push in one go
publish: image push
    @echo "published {{REGISTRY}}/{{IMAGE}}:{{TAG}} (+ :latest)"

# Print the fully-qualified image reference
image-ref:
    @echo "{{REGISTRY}}/{{IMAGE}}:{{TAG}}"

# --- Helm chart (ghcr OCI) ---

# Lint the chart
chart-lint:
    helm lint {{CHART}}

# Render the chart to stdout (sanity check)
chart-template:
    helm template anomaly-exporter {{CHART}}

# Package + push the chart to ghcr OCI (set GHCR_USER + GHCR_TOKEN)
chart-publish:
    echo "${GHCR_TOKEN:?set GHCR_TOKEN to a GitHub PAT with write:packages}" | helm registry login {{REGISTRY}} -u "${GHCR_USER:?set GHCR_USER to your GitHub username}" --password-stdin
    rm -rf /tmp/anomaly-exporter-charts && mkdir -p /tmp/anomaly-exporter-charts
    helm package {{CHART}} -d /tmp/anomaly-exporter-charts
    helm push /tmp/anomaly-exporter-charts/*.tgz "oci://{{REGISTRY}}/{{CHARTS_NAMESPACE}}"

# --- Observability library (observ-viz pack) ---

# Vendor the observ-lib deps (observ-viz) via jsonnet-bundler
observ-lib-vendor:
    cd {{OBSERV_LIB}} && jb install

# Render the observ-lib: dashboards_out/*.json + prometheus_alerts.yaml
observ-lib-build: observ-lib-vendor
    cd {{OBSERV_LIB}} && mkdir -p dashboards_out && jsonnet -J vendor -m dashboards_out lib/dashboards.jsonnet && jsonnet -J vendor -S lib/alerts.jsonnet > prometheus_alerts.yaml

# promtool-test the rendered alerts
observ-lib-test:
    cd {{OBSERV_LIB}} && promtool test rules tests/*.yaml

# Format the observ-lib jsonnet
observ-lib-fmt:
    cd {{OBSERV_LIB}} && find . -name vendor -prune -o \( -name '*.libsonnet' -o -name '*.jsonnet' \) -print | xargs -n 1 jsonnetfmt -i
