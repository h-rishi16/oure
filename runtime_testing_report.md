# OURE Complete Audit — All Confirmed Bugs
_Static analysis + 26 runtime probes · 2026-03-14_

---

## Quick Reference: All Findings

| # | Severity | File | Bug |
|---|---|---|---|
| 1 | 🔴 Critical | [cli/main.py](file:///Users/hrishi/Projects/oure/oure/cli/main.py) | CLI entrypoint has zero registered commands |
| 2 | 🔴 Critical | [physics/sgp4_propagator.py](file:///Users/hrishi/Projects/oure/oure/physics/sgp4_propagator.py) | SGP4 ignores input `r,v` — all states map to TLE orbit |
| 3 | 🔴 Critical | [cli/cmd_fetch.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_fetch.py) L23 | `2 * TWO_PI` gives ISS altitude −2097 km |
| 4 | 🔴 Critical | [cli/cmd_analyze.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_analyze.py) L41–45 | [_tle_to_initial_state](file:///Users/hrishi/Projects/oure/oure/cli/cmd_analyze.py#35-46) ignores inclination & RAAN |
| 5 | 🔴 Critical | [data/spacetrack.py](file:///Users/hrishi/Projects/oure/oure/data/spacetrack.py) L179 | Naive datetime crashes with TypeError on propagation |
| 6 | 🔴 Critical | [risk/foster.py](file:///Users/hrishi/Projects/oure/oure/risk/foster.py) L82 | Foster series Pc wrong by 99.98% (wrong eigenvalue + wrong normalization) |
| 7 | 🔴 Critical | [risk/calculator.py](file:///Users/hrishi/Projects/oure/oure/risk/calculator.py) | [AlertClassifier](file:///Users/hrishi/Projects/oure/oure/risk/alert.py#11-30) never called — `warning_level` always `"GREEN"` |
| 8 | 🔴 Critical | [physics/factory.py](file:///Users/hrishi/Projects/oure/oure/physics/factory.py) | J2 applied twice (SGP4 already includes it) |
| 9 | 🔴 Critical | [physics/frames.py](file:///Users/hrishi/Projects/oure/oure/physics/frames.py) L34–39 | Division-by-zero on circular/equatorial orbits (20 live warnings) |
| 10 | 🟡 Medium | [data/spacetrack.py](file:///Users/hrishi/Projects/oure/oure/data/spacetrack.py) L96–98 | Bulk-fetch cache always returns `[]` when fresh |
| 11 | 🟡 Medium | [data/spacetrack.py](file:///Users/hrishi/Projects/oure/oure/data/spacetrack.py) L72 | [SpaceTrackAuthError](file:///Users/hrishi/Projects/oure/oure/core/exceptions.py#21-23) defined but `ValueError` raised instead |
| 12 | 🟡 Medium | [physics/numerical.py](file:///Users/hrishi/Projects/oure/oure/physics/numerical.py) L109 | `solve_ivp` success never checked — silent NaN on failure |
| 13 | 🟡 Medium | [physics/numerical.py](file:///Users/hrishi/Projects/oure/oure/physics/numerical.py) | Propagates below Earth surface with no error |
| 14 | 🟡 Medium | [conjunction/tca_finder.py](file:///Users/hrishi/Projects/oure/oure/conjunction/tca_finder.py) L63 | [find_tca](file:///Users/hrishi/Projects/oure/oure/conjunction/tca_finder.py#28-64) never returns `None` — returns boundary TCA instead |
| 15 | 🟡 Medium | [data/spacetrack.py](file:///Users/hrishi/Projects/oure/oure/data/spacetrack.py) L167 | RAAN mock range [(0,180)](file:///Users/hrishi/Projects/oure/oure/cli/main.py#47-73) should be [(0,360)](file:///Users/hrishi/Projects/oure/oure/cli/main.py#47-73) |
| 16 | 🟡 Medium | [cli/cmd_fetch.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_fetch.py) L72 | `force_refresh` silently swallowed by `**kwargs`, never acts |
| 17 | 🟡 Medium | [data/noaa.py](file:///Users/hrishi/Projects/oure/oure/data/noaa.py) | No network error handling — NOAA outage crashes everything |
| 18 | 🟡 Medium | [data/noaa.py](file:///Users/hrishi/Projects/oure/oure/data/noaa.py) L65–66 | `f10_7_81day_avg` always == `f10_7`; `ap_index` hardcoded `15.0` |
| 19 | 🟡 Medium | [api/main.py](file:///Users/hrishi/Projects/oure/oure/api/main.py) L76 | Temp file leaked on any exception before `os.unlink` |
| 20 | 🟡 Medium | [conjunction/assessor.py](file:///Users/hrishi/Projects/oure/oure/conjunction/assessor.py) L69 | KD-Tree rebuilt every timestep (up to 8640×) |
| 21 | 🟡 Medium | [uncertainty/monte_carlo.py](file:///Users/hrishi/Projects/oure/oure/uncertainty/monte_carlo.py) | Outlier threshold `9.0` = 82.6% confidence not 3-sigma (99.7%) |
| 22 | 🟡 Medium | [uncertainty/noise.py](file:///Users/hrishi/Projects/oure/oure/uncertainty/noise.py) L18–19 | Process noise Q missing position-velocity cross-terms (`dt²/2`) |
| 23 | 🟡 Medium | [physics/breakup.py](file:///Users/hrishi/Projects/oure/oure/physics/breakup.py) L32 | `v_rel` computed but never used — fragment dispersion ignores impact speed |
| 24 | 🟡 Medium | [uncertainty/stm.py](file:///Users/hrishi/Projects/oure/oure/uncertainty/stm.py) L55 | J2 gradient uses wrong power of `r_mag` |
| 25 | 🟡 Medium | [physics/sgp4_propagator.py](file:///Users/hrishi/Projects/oure/oure/physics/sgp4_propagator.py) L58–78 | TLE epoch / state epoch mismatch in element propagation |
| 26 | 🟡 Medium | [pyproject.toml](file:///Users/hrishi/Projects/oure/pyproject.toml) | `sgp4>=2.22` declared as dependency but **never imported** anywhere |
| 27 | 🟢 Low | [cli/cmd_shatter.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_shatter.py), [cmd_avoid.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_avoid.py) | 3 progress tasks created per command, none ever `.update()`'d |
| 28 | 🟢 Low | [cli/cmd_sensor.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_sensor.py), [cmd_shatter.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_shatter.py), [cmd_avoid.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_avoid.py), [cmd_fetch.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_fetch.py) | Dead [log](file:///Users/hrishi/Projects/oure/oure/data/spacetrack.py#64-74) variable (logger created, never used) |
| 29 | 🟢 Low | [pyproject.toml](file:///Users/hrishi/Projects/oure/pyproject.toml) | `coverage.run.omit` excludes [cli/](file:///Users/hrishi/Projects/oure/oure/cli/main.py#47-73) — real coverage is ~40% not 68% |
| 30 | 🟢 Low | [physics/drag_corrector.py](file:///Users/hrishi/Projects/oure/oure/physics/drag_corrector.py) | Fallback `return 1e-14` is dead code (alt always clipped before it) |
| 31 | 🟢 Low | [uncertainty/sensor.py](file:///Users/hrishi/Projects/oure/oure/uncertainty/sensor.py) L46 | Variable named `I` (ambiguous — looks like number 1) |
| 32 | 🟢 Low | [uncertainty/sensor.py](file:///Users/hrishi/Projects/oure/oure/uncertainty/sensor.py) L47 | Simple form [(I-KH)P](file:///Users/hrishi/Projects/oure/oure/cli/main.py#47-73) used instead of numerically stable Joseph form |
| 33 | 🟢 Low | [data/noaa.py](file:///Users/hrishi/Projects/oure/oure/data/noaa.py) | Uses synchronous `requests` — blocks if called from async context |

---

## CRITICAL BUGS — Full Detail

---

### Bug 1 — CLI Entrypoint Has Zero Commands

**File:** [cli/main.py](file:///Users/hrishi/Projects/oure/oure/cli/main.py) · **Confirmed by:** `list(cli.commands.keys()) == []`

Every subcommand file ([cmd_analyze.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_analyze.py), [cmd_cache.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_cache.py), etc.) registers to [cli](file:///Users/hrishi/Projects/oure/oure/cli/main.py#47-73) via `@cli.command()`, but only when the file is imported. [main.py](file:///Users/hrishi/Projects/oure/oure/cli/main.py) has no imports of those files. Running `oure cache --status` produces `Error: No such command 'cache'`. The entire CLI is broken at the entrypoint.

**Fix:** Add at the bottom of [main.py](file:///Users/hrishi/Projects/oure/oure/cli/main.py):
```python
from oure.cli import (  # noqa: E402, F401
    cmd_analyze, cmd_avoid, cmd_cache, cmd_cdm,
    cmd_fetch, cmd_fleet, cmd_history, cmd_monitor,
    cmd_plot, cmd_report, cmd_sensor, cmd_shatter,
)
```

---

### Bug 2 — SGP4 Completely Ignores Input State Vectors

**File:** [physics/sgp4_propagator.py](file:///Users/hrishi/Projects/oure/oure/physics/sgp4_propagator.py) · **Confirmed by:** Two states (7000 km and 42000 km) → identical output

[propagate_many_to()](file:///Users/hrishi/Projects/oure/oure/physics/numerical.py#164-182) extracts only `nu0` (true anomaly) from the input `r,v` using [rv2coe_vectorized](file:///Users/hrishi/Projects/oure/oure/physics/frames.py#11-42). All other elements (`a`, `e`, `i`, `RAAN`, `ω`) come from the TLE. So two calls with wildly different states produce the same trajectory. The [propagate(state, dt)](file:///Users/hrishi/Projects/oure/oure/physics/sgp4_propagator.py#47-50) interface is misleading — it behaves like `propagate_from_tle(tca_offset)`.

---

### Bug 3 — `2 * TWO_PI` Gives Negative Altitudes

**File:** [cli/cmd_fetch.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_fetch.py#L23) · **Confirmed by:** ISS altitude reported as −2097 km

```python
# BROKEN (uses 4π instead of 2π):
n = mean_motion_rev_per_day * 2 * constants.TWO_PI / constants.SECONDS_PER_DAY
# CORRECT:
n = mean_motion_rev_per_day * constants.TWO_PI / constants.SECONDS_PER_DAY
```
`TWO_PI` is already `2π`. The `2 *` doubles it to `4π`, halving `n`, which cubes the error in `a = (μ/n²)^(1/3)`. Same bug in `cmd_analyze._tle_to_initial_state()` L39. All altitude displays and all initial states generated from TLEs are numerically wrong.

---

### Bug 4 — [_tle_to_initial_state](file:///Users/hrishi/Projects/oure/oure/cli/cmd_analyze.py#35-46) Forces All Orbits Into Equatorial Plane

**File:** [cli/cmd_analyze.py](file:///Users/hrishi/Projects/oure/oure/cli/cmd_analyze.py#L41-L45) · **Confirmed by:** `r[2]` is always 0.0

```python
r = a * np.array([cos(M), sin(M), 0.0])   # z always zero — equatorial!
v = v_mag * np.array([-sin(M), cos(M), 0.0])
```
Inclination and RAAN are never applied. The ISS (51.6° inclination) can be ±5300 km in z. This is the initial state fed to conjunction screening and the Celery background task — the entire 3D geometry is wrong for every non-equatorial satellite.

---

### Bug 5 — Naive Datetime Crashes at Runtime

**File:** [data/spacetrack.py](file:///Users/hrishi/Projects/oure/oure/data/spacetrack.py#L179) · **Confirmed by:** `TypeError: can't subtract offset-naive and offset-aware datetimes`

```python
# BROKEN — produces naive datetime:
epoch = datetime.strptime(epoch_str, "%Y-%m-%d %H:%M:%S")
# FIX:
epoch = datetime.strptime(epoch_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
```
The conftest fixture manually injects `tzinfo=UTC`, masking this crash in tests. Production always crashes.

---

### Bug 6 — Foster Series Pc Is Wrong by 99.98%

**File:** [risk/foster.py](file:///Users/hrishi/Projects/oure/oure/risk/foster.py#L82) · **Confirmed by:** Numerical=1.63e-4 vs Series=3.53e-8

Two compounding errors:
1. `lam1` (smaller eigenvalue) used where `lam2` (larger) is specified by Foster's formula
2. Extra `pi` in normalization: code divides by `2 * pi * sqrt(lam1*lam2)` but formula requires `2 * sqrt(lam1*lam2)`

Additionally the numerical integration method triggers a `scipy IntegrationWarning: maximum subdivisions (50) achieved` for elongated covariances, meaning neither method is reliable.

---

### Bug 7 — `warning_level` Is Always "GREEN"

**File:** [risk/calculator.py](file:///Users/hrishi/Projects/oure/oure/risk/calculator.py) + [risk/alert.py](file:///Users/hrishi/Projects/oure/oure/risk/alert.py) · **Confirmed by:** `'AlertClassifier' in src == False`

`RiskResult.warning_level` defaults to `"GREEN"`. `AlertClassifier.classify()` exists and correctly thresholds RED/YELLOW/GREEN — but it is never called anywhere in [compute_pc()](file:///Users/hrishi/Projects/oure/oure/risk/calculator.py#26-46). The alert module is completely disconnected from the pipeline. Every conjunction event reports GREEN regardless of Pc value.

**Fix:** In [calculator.py](file:///Users/hrishi/Projects/oure/oure/risk/calculator.py):
```python
from oure.risk.alert import AlertClassifier
# in compute_pc(), after computing pc:
alert = AlertClassifier()
warning_level = alert.classify(pc)
return RiskResult(..., warning_level=warning_level)
```

---

## MEDIUM BUGS — Key Details

---

### Bug 17 — NOAA Fetcher Has No Error Handling

**File:** [data/noaa.py](file:///Users/hrishi/Projects/oure/oure/data/noaa.py)

```python
def _fetch_from_network(self) -> list:
    resp = requests.get(self.FLUX_URL, timeout=20)
    resp.raise_for_status()   # no except — ConnectionError propagates to caller
    ...
```
If NOAA is unreachable (very common in isolated environments), `ConnectionError` or `HTTPError` propagates all the way up to the CLI and crashes. There's no fallback to the default solar mean of 150 sfu.

**Fix:**
```python
try:
    resp = requests.get(self.FLUX_URL, timeout=20)
    resp.raise_for_status()
except Exception:
    logger.warning("NOAA unreachable, using default F10.7=150")
    return [SolarFluxData(date=datetime.now(UTC), f10_7=150.0, ...)]
```

---

### Bug 18 — NOAA Solar Data Is Partially Fabricated

**File:** [data/noaa.py](file:///Users/hrishi/Projects/oure/oure/data/noaa.py#L63-L66)

```python
f10_7=float(data.get("Flux", 150.0)),
f10_7_81day_avg=float(data.get("Flux", 150.0)),  # always identical to f10_7
ap_index=15.0   # never fetched — hardcoded to "moderate activity"
```
The 81-day F10.7 average and Ap geomagnetic index are essential for atmosphere density models. Both are fabricated. The NOAA archive URL (`FLUX_ARCHIVE_URL`) is defined but never fetched.

---

### Bug 19 — API Temp File Leaked on Exception

**File:** [api/main.py](file:///Users/hrishi/Projects/oure/oure/api/main.py#L66-L76) · **Confirmed by:** file persists after exception

```python
with tempfile.NamedTemporaryFile(delete=False, ...) as temp_file:
    ...
    temp_path = temp_file.name

event = CDMParser.parse_json(temp_path)   # can raise
calc.compute_pc(event)                    # can raise BPlaneError

os.unlink(temp_path)   # ← NEVER reached if exception thrown above
```
Every failed CDM upload leaks a temp file. Under sustained load this exhausts `/tmp` space.

**Fix:** Use `try/finally`:
```python
try:
    event = CDMParser.parse_json(temp_path)
    result = calc.compute_pc(event)
finally:
    os.unlink(temp_path)
```

---

### Bug 21 — Monte Carlo Outlier Threshold Is Statistically Wrong

**File:** [uncertainty/monte_carlo.py](file:///Users/hrishi/Projects/oure/oure/uncertainty/monte_carlo.py) · **Confirmed by:** chi2.cdf(9.0, df=6) = 82.6%

```python
outlier_mask = distances > 9.0   # intends to be "3-sigma" outliers
```
For a 6-dimensional state vector, the Mahalanobis distance squared follows χ²(df=6). The 3-sigma (99.73%) threshold is `χ²(df=6, p=0.9973) = 22.46`. Using 9.0 discards only the outermost 17.4% of samples — not 0.27% as intended. This throws away valid samples and biases the reconstructed covariance matrix.

**Fix:**
```python
from scipy.stats import chi2
threshold = chi2.ppf(0.9973, df=6)   # = 22.46
outlier_mask = distances > threshold
```

---

### Bug 22 — Process Noise Q Missing Cross-Terms

**File:** [uncertainty/noise.py](file:///Users/hrishi/Projects/oure/oure/uncertainty/noise.py#L17-L19) · **Confirmed by:** `Q[:3, 3:] == zeros`

A proper PWNA process noise matrix has four non-zero blocks:

```python
Q[:3, :3] = I * q * dt³/3    # position (present)
Q[3:, 3:] = I * q * dt       # velocity (present)
Q[:3, 3:] = I * q * dt²/2    # MISSING
Q[3:, :3] = I * q * dt²/2    # MISSING
```
Without the cross-terms, position and velocity uncertainties are uncorrelated through the noise model, leading to an incorrect covariance shape over long propagations.

---

### Bug 23 — `BreakupModel.simulate_collision` Ignores Impact Speed

**File:** [physics/breakup.py](file:///Users/hrishi/Projects/oure/oure/physics/breakup.py#L32) · **Confirmed by:** `v_rel` only used in a log message

```python
v_rel = np.linalg.norm(v1 - v2)  # computed...
# ...
logger.info(f"V_rel = {v_rel:.2f} km/s")  # ...only used here
```
All fragments use hardcoded `mu_log_dv = -0.5`, `sigma_log_dv = 0.55` regardless of whether the collision is 1 km/s (grazing) or 15 km/s (head-on). The NASA Standard Breakup Model explicitly ties fragment speed distribution to impact velocity.

---

### Bug 26 — `sgp4` Library Is a Ghost Dependency

**File:** [pyproject.toml](file:///Users/hrishi/Projects/oure/pyproject.toml) · **Confirmed by:** `grep -r 'from sgp4' oure/` returns nothing

```toml
dependencies = [
    "sgp4>=2.22",   # listed but NEVER imported
    ...
]
```
The project ships its own simplified SGP4 in `sgp4_propagator.py` (≈80 lines) instead of using the well-tested `sgp4` library (which uses the official C-extension Vallado implementation). The homebrew version lacks:
- Atmospheric drag correction in mean elements
- Deep-space resonance terms
- Luni-solar perturbations for high-altitude objects
- The SDP4 model for periods > 225 minutes

---

## LOW SEVERITY

### Bug 27 — Progress Spinners Never Advance

**Files:** `cmd_shatter.py`, `cmd_avoid.py` — 3 tasks per command, 0 ever updated

```python
task = progress.add_task("Shattering into N fragments...")
debris_states = BreakupModel.simulate_collision(...)  # can take seconds
# progress.update(task, ...) ← never called
```
The spinner rotates but the bar never moves and completion is never reported. UX issue but also signals the progress tracking design is un-integrated.

### Bug 29 — Coverage Config Hides Real Test Gaps

```toml
[tool.coverage.run]
omit = ["*/oure/cli/*", "*/tests/*"]
```
CLI directory excluded entirely. Reported: **68%**. Actual (including CLI): **~40%**. Eight modules at 0% include `NumericalPropagator`, `CDMParser`, `ManeuverPropagator`, `BreakupModel`, `SensorTaskingSimulator`, `RiskPlotter`, `ManeuverOptimizer`, and `logging_config`.

### Bug 30 — Dead Code in `drag_corrector._atmospheric_density`

The altitude is `np.clip`'d to `[200, 700]` before the lookup loop. The final `return 1e-14` fallback after the loop is unreachable for any valid input (the 600–700 km bucket always matches `alt=700`).

---

## Test Health Summary

| Metric | Value |
|---|---|
| Tests passing | 33 / 37 |
| Tests failing | 4 (all CLI, all same root cause: Bug 1) |
| Live RuntimeWarnings | 20 (frames.py divide, sgp4 sqrt) |
| Reported coverage | 68% |
| True coverage (incl. CLI) | ~40% |
| Modules at 0% coverage | 8 |
| Foster series Pc error | 99.98% |
