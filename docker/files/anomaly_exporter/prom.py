"""Minimal Prometheus ``query_range`` client.

Issues a single range query, with optional tenant (``X-Scope-OrgID``) and
bearer-token headers for Mimir / Cortex / authenticated Prometheus.
"""
from __future__ import annotations

import time

import requests


class PromError(Exception):
    """The Prometheus API returned a non-success status."""


class PromClient:
    def __init__(self, url: str, tenant: str = "", token: str = "", timeout: float = 60.0):
        self.url = url.rstrip("/")
        self.tenant = tenant
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict:
        h = {}
        if self.tenant:
            h["X-Scope-OrgID"] = self.tenant  # Mimir/Cortex multitenancy
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def query_range(self, query, lookback_s, step, timeout=None, now=None):
        """Range-query ``query`` over the last ``lookback_s`` seconds at ``step``.

        Returns the raw ``data.result`` list (one entry per series, each with
        ``metric`` labels and ``values`` ``[ts, value]`` pairs).
        """
        end = int(now if now is not None else time.time())
        start = end - int(lookback_s)
        resp = requests.get(
            f"{self.url}/api/v1/query_range",
            params={"query": query, "start": start, "end": end, "step": step},
            headers=self._headers(),
            timeout=timeout or self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != "success":
            raise PromError(f"query failed: {payload.get('error', payload)}")
        return payload["data"]["result"]
