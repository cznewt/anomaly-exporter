#!/usr/bin/env just --justfile

# Image coordinates (override on the CLI, e.g. `just TAG=dev publish`)
REGISTRY := "ghcr.io"
IMAGE := "cznewt/anomaly-exporter"
TAG := `cat VERSION`

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
