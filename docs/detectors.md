# Detectors

A detector turns one Prometheus series into a single anomaly score from `0`
(normal) to `1` (anomalous). All detectors share the same scaffold and differ only
in how they score a point, so you can swap detectors per module and alert on the
output uniformly.

## The shared scoring scaffold

Every detector follows the same steps (see `detectors/base.py`):

1. **Build a frame** of `(timestamp, value)` pairs from the query result and drop
   gaps (NaN samples).
2. **Guard**: if the series has fewer than `min_train_points + eval_points`
   samples, it is skipped (counted in `anomaly_series_total` but not
   `anomaly_series_scored`).
3. **Split**: the trailing `eval_points` samples are the **scored window**;
   everything before them is the **training window** (the baseline). Scoring the
   most recent points against an earlier baseline keeps a fresh anomaly from
   poisoning its own reference.
4. **Score** each point in the scored window from `0` to `1`.
5. **Reduce**: the series score is the **worst (maximum)** point in the scored
   window. That single number is published as `anomaly_score{<labels>}`.

So `eval_points` is "how much recent history counts as now" (e.g. `12` points at
`5m` is the last hour), and `lookback` decides how much baseline the detector
gets to learn from.

| Detector | Dependencies | Models trend? | Models seasonality? | Relative cost |
| :--- | :--- | :--- | :--- | :--- |
| `prophet` | prophet (+ cmdstan) | yes | yes | highest |
| `holt_winters` | statsmodels | yes | yes (set `season_length`) | medium |
| `ewma` | pandas | drift only | no | low |
| `iqr` | pandas | no | no | lowest |
| `zscore` | pandas | no | no | lowest |
| `mean_sigma` | pandas | no | no | lowest |

The four lightweight detectors (`iqr`, `zscore`, `mean_sigma`, `ewma`) have no
notion of seasonality, so a strongly cyclic signal's normal peaks read as
deviations. Use a seasonal detector (`prophet` or `holt_winters`) for those.

---

## prophet

Fits a [Prophet](https://facebook.github.io/prophet/) model (additive trend plus
daily/weekly seasonality) on the training window, predicts the scored window, and
compares each actual point against Prophet's uncertainty band
`[yhat_lower, yhat_upper]` (its width set by `interval_width`).

**Score per point**: `0` if the point is inside the band, otherwise the distance
outside the band divided by the band width, capped at `1`.

**Parameters** (block key `prophet:`):

| Param | Default | Meaning |
| :--- | :--- | :--- |
| `interval_width` | `0.95` | Width of the uncertainty band. Wider = more tolerant. |
| `daily_seasonality` | `auto` | `auto`, `true`, `false`, or an integer number of Fourier terms. |
| `weekly_seasonality` | `auto` | Same accepted values. |

**Use it when** the metric has genuine trend or daily/weekly seasonality and you
want the band to follow that shape. **Costs**: it is the heaviest option (a model
fit per series per probe) and pulls in Prophet and its Stan backend. Give modules
that use it a generous `scrape_timeout`, and enough `lookback` to cover at least a
couple of seasonal cycles.

**Config sample**:

```yaml
modules:
  mem-prophet:
    detector: prophet
    lookback: 7d
    step: 5m
    eval_points: 12          # last hour at 5m resolution
    min_train_points: 30
    labels: [namespace, pod]
    timeout: 120s            # Prophet fits are slow; give the probe headroom
    prophet:
      interval_width: 0.95
      daily_seasonality: true
      weekly_seasonality: auto
```

---

## holt_winters

Triple exponential smoothing (Holt-Winters, via
[statsmodels](https://www.statsmodels.org/)) on the training window: level, trend,
and an optional seasonal component of length `season_length`. It forecasts the
scored window and builds a band of `k` residual standard deviations
(`k * std(fitted - actual)` over the training window) around the forecast.

**Score per point**: `|actual - forecast| / (k * residual_sigma)`, capped at `1`.

**Parameters** (block key `holt_winters:`):

| Param | Default | Meaning |
| :--- | :--- | :--- |
| `season_length` | `0` | Steps in one cycle. `0` fits trend only. Example: a day is `288` at `5m`, `48` at `30m`. |
| `trend` | `add` | `add` for an additive trend, or `none`. |
| `seasonal` | `add` | `add` or `mul` (used only when `season_length` is set). |
| `k` | `3` | Band half-width in residual sigmas. Lower = more sensitive. |

The seasonal component is only fit when the training window holds at least two
full seasons (`len(train) >= 2 * season_length`); otherwise it degrades to a
trend-only fit. **Use it when** you want seasonality awareness without Prophet's
weight. **Costs**: needs a fairly regular series and a correct `season_length`; a
wrong `season_length` makes normal data look anomalous.

**Config sample**:

```yaml
modules:
  traffic-holt-winters:
    detector: holt_winters
    lookback: 7d
    step: 30m
    eval_points: 6           # last 3h at 30m resolution
    labels: [route]
    holt_winters:
      season_length: 48      # one day at 30m resolution
      trend: add
      seasonal: add
      k: 3
```

---

## iqr

A robust [interquartile-range](https://en.wikipedia.org/wiki/Interquartile_range#Outliers)
(Tukey) fence built from the training window. With `Q1`, `Q3`, and
`IQR = Q3 - Q1`, the fence is `[Q1 - k*IQR, Q3 + k*IQR]`.

**Score per point**: `0` inside the fence, otherwise the distance outside divided
by the fence width, capped at `1`.

**Parameters** (block key `iqr:`):

| Param | Default | Meaning |
| :--- | :--- | :--- |
| `k` | `1.5` | Fence multiplier. `1.5` flags mild outliers, `3.0` only far ones. |

**Use it when** the metric is flat-ish or noisy and you want something
training-free, fast, and robust to a few bad points in the baseline. **Costs**: no
trend or seasonality model.

**Config sample**:

```yaml
modules:
  cpu-iqr:
    detector: iqr
    lookback: 1d
    step: 1m
    eval_points: 10
    labels: [pod]
    iqr:
      k: 1.5
```

---

## zscore

A robust z-score from the training window's **median** and **median absolute
deviation** (MAD). The robust sigma is `1.4826 * MAD` (which equals one standard
deviation for normal data). If MAD collapses to `0` on a near-constant baseline,
it falls back to the standard deviation, then to a neutral scale, so a flat series
never divides by zero.

**Score per point**: `|value - median| / (1.4826 * MAD) / z_max`, capped at `1`.

**Parameters** (block key `zscore:`):

| Param | Default | Meaning |
| :--- | :--- | :--- |
| `z_max` | `4` | Robust sigmas that map to a full score of `1.0`. Lower = more sensitive. |

**Use it when** you want a smooth severity ramp (rather than an in/out band) on a
flat-ish metric, with a baseline that resists spikes. **Costs**: no trend or
seasonality model.

**Config sample**:

```yaml
modules:
  latency-zscore:
    detector: zscore
    lookback: 1d
    step: 1m
    labels: [service]
    zscore:
      z_max: 4
```

---

## mean_sigma

The classic, non-robust sibling of `zscore`: it uses the plain **mean** and
**standard deviation** of the training window. Cheapest of all detectors and a
good fit for clean, roughly-normal baselines where you do not need outlier
resistance.

**Score per point**: `|value - mean| / stddev / z_max`, capped at `1`. A flat
baseline (zero stddev) uses a neutral scale to avoid dividing by zero.

**Parameters** (block key `mean_sigma:`):

| Param | Default | Meaning |
| :--- | :--- | :--- |
| `z_max` | `4` | Standard deviations that map to a full score of `1.0`. |

**Use it when** the baseline is clean and roughly normal. **Costs**: not robust (a
single large value in the training window inflates both mean and stddev); no trend
or seasonality model.

**Config sample**:

```yaml
modules:
  rps-mean-sigma:
    detector: mean_sigma
    lookback: 6h
    step: 1m
    labels: [job]
    mean_sigma:
      z_max: 4
```

---

## ewma

An exponentially-weighted moving-average control band. The mean and the residual
sigma are both EWMA series, each shifted by one step so a point is judged only
against the points **before** it (a causal band). This lets the baseline track
slow drift instead of treating a gradual level change as an anomaly.

**Score per point**: `|value - ewma_mean| / (k * ewma_sigma)`, capped at `1`.
Points where the band is not yet defined (or sigma is zero) score `0`.

**Parameters** (block key `ewma:`):

| Param | Default | Meaning |
| :--- | :--- | :--- |
| `span` | `12` | EWMA span (larger = smoother, slower to adapt). |
| `alpha` | _(unset)_ | Smoothing factor; overrides `span` when set. |
| `k` | `3` | Band half-width in residual sigmas. |

**Use it when** the baseline drifts over time and a fixed fence would constantly
trip. **Costs**: no seasonality; needs some variance to form a sigma, and by
design it tolerates sustained level shifts.

**Config sample**:

```yaml
modules:
  queue-ewma:
    detector: ewma
    lookback: 12h
    step: 1m
    labels: [queue]
    ewma:
      span: 24
      k: 3
```

---

## Choosing a detector

- **Has daily/weekly seasonality** (request rates, user-facing traffic): start
  with `prophet`; switch to `holt_winters` if probe latency or dependencies
  matter, setting `season_length` to the steps in one cycle.
- **Flat-ish or noisy, no clear cycle** (error counts, queue depth): `iqr` for a
  robust in/out fence, or `zscore` for a smooth severity ramp.
- **Slowly drifting baseline** (saturating caches, growing backlogs): `ewma`.
- **Clean and roughly normal, want the cheapest check**: `mean_sigma`.

## Adding a detector

Detection is a pluggable registry. To add one:

1. Create `docker/files/anomaly_exporter/detectors/mything.py` with a `Detector`
   subclass that implements `point_scores(self, df, train_df, eval_df)` and
   returns one score from `0` to `1` per row of `eval_df`:

   ```python
   from .base import Detector

   class MyThingDetector(Detector):
       name = "mything"

       def point_scores(self, df, train_df, eval_df):
           k = float(self.params.get("k", 3.0))
           baseline = train_df["y"].mean()
           spread = train_df["y"].std(ddof=0) or 1.0
           return [min(abs(v - baseline) / (k * spread), 1.0) for v in eval_df["y"]]
   ```

2. Register it in `detectors/__init__.py` by adding `MyThingDetector` to the
   `DETECTORS` tuple.
3. Reference it from config: `detector: mything` with an optional `mything:` block
   for its parameters.

Keep any heavy third-party imports **inside** `point_scores` (as `prophet` and
`holt_winters` do) so that importing the registry, listing detectors, and
validating config stay light and dependency-free.
