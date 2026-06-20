"""Command-line entrypoint: ``python -m anomaly_exporter``.

Flag names mirror the Prometheus ecosystem (``--config.file``,
``--web.listen-address``) so it feels like blackbox_exporter to operate.
"""
from __future__ import annotations

import argparse
import logging
import os

from .app import create_app
from .config import load_config


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="anomaly-exporter",
        description="Blackbox-style anomaly exporter for Prometheus.",
    )
    p.add_argument(
        "--config.file", dest="config_file",
        default=os.environ.get("ANOMALY_EXPORTER_CONFIG", "config.yml"),
        help="path to the config file (default: $ANOMALY_EXPORTER_CONFIG or config.yml)",
    )
    p.add_argument(
        "--web.listen-address", dest="listen", default=":9888",
        help="address to listen on (default: :9888)",
    )
    p.add_argument("--threads", type=int, default=8, help="waitress worker threads (default: 8)")
    p.add_argument(
        "--log.level", dest="log_level",
        default=os.environ.get("LOG_LEVEL", "INFO"), help="log level (default: INFO)",
    )
    p.add_argument("--dev", action="store_true", help="use Flask's dev server instead of waitress")
    return p.parse_args(argv)


def _split_addr(listen: str):
    host, _, port = listen.rpartition(":")
    return (host or "0.0.0.0"), int(port)


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(args.config_file)
    app = create_app(config)
    host, port = _split_addr(args.listen)
    log = logging.getLogger("anomaly-exporter")
    log.info(
        "listening on %s:%d - %d module(s): %s",
        host, port, len(config.modules), ", ".join(sorted(config.modules)),
    )
    if args.dev:
        app.run(host=host, port=port, threaded=True)
    else:
        from waitress import serve

        serve(app, host=host, port=port, threads=args.threads)


if __name__ == "__main__":
    main()
