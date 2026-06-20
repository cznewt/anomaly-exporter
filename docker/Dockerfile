# Blackbox-style anomaly exporter for Prometheus.
#
# A single exporter that runs PromQL range queries on demand and scores them for
# anomalies with a config-selected detector (prophet / iqr / zscore / mean_sigma
# / ewma / holt_winters), following Prometheus' multi-target (blackbox_exporter)
# pattern:  GET /probe?module=<name>&target=<promql>
# Configuration is a YAML file (see README.md), not env vars.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libgomp1: OpenMP runtime required by Prophet's bundled Stan model.
RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY files/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY files/anomaly_exporter /app/anomaly_exporter
COPY files/config.yml /etc/anomaly-exporter/config.yml

ENV ANOMALY_EXPORTER_CONFIG=/etc/anomaly-exporter/config.yml

EXPOSE 9888

RUN useradd --create-home --uid 10001 exporter
USER exporter

ENTRYPOINT ["python", "-m", "anomaly_exporter"]
CMD ["--config.file=/etc/anomaly-exporter/config.yml", "--web.listen-address=:9888"]
