# OURE — Senior Developer Code Review

**Repository:** `https://github.com/h-rishi16/OURE`
**Version reviewed:** `1.1.0`
**Reviewer:** Claude (Sonnet 4.6)
**Review scope:** Full source — 77 files, all layers

---

## Executive Summary

The architecture is legitimately excellent. The AST-based layer enforcement test, the custom exception hierarchy, the Decorator propagator chain, and the SLSQP optimizer pre-caching the secondary TCA state all show real engineering judgment. The gap is between **"it runs"** and **"it computes the right answers."** Several physics bugs silently produce wrong Pc values, CI never runs due to a branch name mismatch, and the most important test — a numerical Pc validation — is missing entirely.

**Overall scores:**

| Dimension | Score | Verdict |
|---|---|---|
| Architecture | 9/10 | Excellent — AST enforcement is production-grade |
| Code Quality | 8/10 | Strong, with a few real smells |
| Physics Rigour | 6/10 | Euler J2, wrong B-plane projection, silent default covariance |
| Test Quality | 7/10 | Good coverage, but no numerical validation |
| CI / DevOps | 4/10 | CI never runs; badge is hardcoded |
| Security | 6/10 | Credential copy bug in installer |

---

## Part 1 — Genuine Strengths

### 1.1 Architecture enforcement via AST test

`tests/integration/test_architecture.py` walks the Python AST and fails the build if any layer imports from the wrong sibling. This is the correct way to enforce decoupling — not documentation, not convention, but a failing CI job. Very few production codebases do this.

### 1.2 Custom exception hierarchy

`core/exceptions.py` defines `OUREBaseError → PropagationError → KeplerConvergenceError` etc. — a proper domain exception tree used consistently throughout the physics layer. `KeplerConvergenceError` is raised with a meaningful message in `kepler.py`. This is production-grade error handling.

### 1.3 Joseph-form Kalman update

In `sensor.py`:

```
P+ = (I - KH) P (I - KH)ᵀ + K R Kᵀ
```

This is mathematically correct and numerically stable. The standard form `P+ = (I - KH)P` is faster but loses positive-definiteness due to floating-point errors. Using the Joseph form here is the right choice.

### 1.4 Propagator decorator chain

`PropagatorFactory.build()` returns `AtmosphericDragCorrector(J2PerturbationCorrector(SGP4Propagator))` — a clean decorator chain. All share the `BasePropagator` ABC. The test in `test_factory.py` verifies the chain structure by type. Correct and testable.

### 1.5 Retry logic with tenacity

`_RETRY_POLICY` in `spacetrack.py` uses exponential backoff (2s → 60s) on `TimeoutException` and `ConnectError`. The mock TLE fallback on network failure is a good offline-mode decision for a CLI tool.

### 1.6 Vectorized Monte Carlo with Cholesky sampling

`monte_carlo.py` uses Cholesky decomposition for correlated sampling, runs `propagate_many_to` in one batched call, and uses chi-squared Mahalanobis outlier detection. The regularization fallback (`+ 1e-12 * I`) is also the right fix for near-singular covariances.

### 1.7 Golden-section TCA finder with coarse scan guard

`tca_finder.py` does an 8-point coarse scan before golden-section refinement, which avoids wasting 100 iterations when no minimum exists. The 10 km miss-distance filter also gates out false positives.

### 1.8 SLSQP optimizer pre-computes secondary state

In `optimizer.py`, the secondary TCA state is propagated once before the SLSQP loop and reused if the TCA hasn't shifted more than 60 seconds. This avoids re-propagating an unmanoeuvred satellite on every objective function evaluation — a real performance win.

---

## Part 2 — Physics Bugs (affect Pc correctness)

### 2.1 🔴 CRITICAL — J2 corrector applies Euler integration, not RK4

**File:** `oure/physics/j2_corrector.py`

```python
# Current — first-order Euler
dv = a_j2 * dt
dr = 0.5 * a_j2 * dt**2
```

This is first-order Euler integration of the J2 acceleration. Over a 72-hour look-ahead with a 30-second timestep, Euler integration accumulates position errors of tens of kilometres. Additionally, SGP4 already includes J2 secular effects internally — layering this Euler corrector on top of SGP4 results in **double-counting J2**.

**Fix:** Apply closed-form secular drift rates instead of integrating the acceleration:

```python
# Secular RAAN and argument of perigee drift (Brouwer theory)
n = np.sqrt(MU / a**3)
p = a * (1 - e**2)
j2_factor = -1.5 * J2 * (R_EARTH / p)**2 * n

raan_dot  = j2_factor * cos(i)                    # rad/s
omega_dot = j2_factor * (2.5 * cos(i)**2 - 0.5)  # rad/s

raan  += raan_dot  * dt
omega += omega_dot * dt
```

This is O(1), exact, and has zero accumulated error.

---

### 2.2 🔴 CRITICAL — `_tle_to_initial_state` uses a bare 10-iteration loop with no convergence check

**File:** `oure/cli/utils.py`

```python
# Current
E = M
for _ in range(10):
    E = E - (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
```

For high-eccentricity TLEs (e > 0.3), 10 iterations may not converge. You already have `solve_kepler_vectorized()` in `kepler.py` that raises `KeplerConvergenceError` on non-convergence — use that here. Right now two independent Kepler solvers exist with inconsistent convergence guarantees.

**Fix:**

```python
from oure.physics.kepler import solve_kepler_vectorized
E = solve_kepler_vectorized(np.array([M]), np.array([e]))[0]
```

---

### 2.3 🔴 CRITICAL — Default covariance is physically wrong and silently used

**File:** `oure/cli/utils.py`

```python
def _default_covariance(sat_id: str) -> CovarianceMatrix:
    P = np.diag([1.0, 1.0, 1.0, 1e-6, 1e-6, 1e-6])
    return CovarianceMatrix(matrix=P, epoch=datetime.now(UTC), sat_id=sat_id)
```

`1.0 km²` position variance = 1 km 1-sigma uncertainty. Real LEO TLE position errors are typically 100 m–500 m. Using 1 km inflates Pc by up to an order of magnitude. There is no log warning or user-facing message that a default is being used. Every Pc output from the standard CLI pipeline is silently wrong unless real covariances are provided via CDM.

**Fix:**

```python
def _default_covariance(sat_id: str, sigma_km: float = 0.5) -> CovarianceMatrix:
    logger.warning(
        f"No covariance for {sat_id} — using default {sigma_km} km sigma. "
        "Pc outputs may be inaccurate. Provide a CDM for calibrated results."
    )
    P = np.diag([sigma_km**2]*3 + [1e-6]*3)
    return CovarianceMatrix(matrix=P, epoch=datetime.now(UTC), sat_id=sat_id)
```

---

### 2.4 🟠 MODERATE — B-plane projection ignores velocity covariance

**File:** `oure/risk/bplane.py`

```python
# Current — position-only (wrong)
C_combined_3d = C_primary[:3, :3] + C_secondary[:3, :3]
C_2d = T @ C_combined_3d @ T.T   # T is 2x3
```

For Foster's method the projection matrix should map the full 6×6 covariance through a 2×6 transformation that accounts for the encounter geometry. The standard formulation is `C_bplane = T_full @ C_6x6 @ T_full.T` where `T_full` is 2×6. Ignoring the velocity covariance block underestimates the total encounter uncertainty.

---

### 2.5 🟠 MODERATE — Foster series u=0 edge case returns wrong weight for n>0

**File:** `oure/risk/foster.py`

```python
else:
    weight = 1.0 if n == 0 else 0.0   # BUG: all n>0 terms dropped when u=0
```

When the miss vector `b` is near zero (a near-head-on conjunction), `u ≈ 0`. The condition above sets `weight = 0` for all `n > 0`, truncating the series at the first term and severely underestimating Pc. Remove the `else` branch and floor-clamp `u` to a small epsilon before entering the log-space path.

Also: 200 series terms is unnecessary — convergence typically occurs in 20–30 terms for LEO conjunctions.

---

### 2.6 🟠 MODERATE — Drag corrector unit consistency is fragile

**File:** `oure/physics/drag_corrector.py`

The drag formula converts `v_mag_ms = v_mag * 1000` (km/s → m/s), uses `rho` in kg/m³, and `am_ratio` in m²/kg. The chain is dimensionally correct but fragile — a single missing factor produces errors of 10⁶×. Add a unit test asserting the drag deceleration at 400 km altitude matches the known ~10⁻⁷ km/s² range.

---

## Part 3 — Code Quality Issues

### 3.1 🟠 `NumericalPropagator` instantiates `AtmosphericDragCorrector` with `None` base

**File:** `oure/physics/numerical.py`

```python
self._drag_model = AtmosphericDragCorrector(
    base_propagator=None,  # type: ignore
    ...
)
```

**Fix:** Extract `_atmospheric_density()` into a standalone `AtmosphericModel` class in `oure/physics/atmosphere.py` and call it directly from both `AtmosphericDragCorrector` and `NumericalPropagator`.

---

### 3.2 🟠 `cmd_fetch.py` redefines `console`, shadowing the import

**File:** `oure/cli/cmd_fetch.py`

```python
from .utils import UI, console   # imports themed OURE console
...
console = Console()               # immediately overwrites with unthemed console
```

All output from `cmd_fetch` loses the OURE brand theme. Delete the local redefinition.

---

### 3.3 🔴 `install.sh` copies credentials into the repo directory

**File:** `install.sh`

```bash
cp "$INSTALL_DIR/keys.env" ./keys.env   # writes credentials into git repo dir
```

If a user runs `git add .` after installing, credentials are committed. Remove this line.

Additionally, the global wrapper uses:

```bash
export $(grep -v '^#' "$INSTALL_DIR/keys.env" | xargs)
```

Passwords with spaces, backticks, or `$()` cause silent truncation or shell injection.

**Fix:**

```bash
set -o allexport
source "$INSTALL_DIR/keys.env"
set +o allexport
```

---

### 3.4 🟠 `dashboard/app.py` uses a bare relative path for mock data

```python
with open("mock_results.json") as f:    # breaks when CWD != project root
```

**Fix:**

```python
data_file = Path(__file__).parent.parent.parent / "mock_results.json"
with open(data_file) as f:
```

---

### 3.5 🟡 Coverage threshold doesn't match the badge

```toml
# pyproject.toml
cov-fail-under=80   # enforced
# README badge claims 88%
```

Set `cov-fail-under=88` to make the badge honest and enforced.

---

### 3.6 🔴 `ci.yml` triggers on `main` but default branch is `master`

**File:** `.github/workflows/ci.yml`

```yaml
on:
  push:
    branches: [ main ]   # wrong — repo uses master
```

**CI never runs on any push.** This is the highest-priority devops fix.

**Fix:** Change to `branches: [ master ]`.

---

### 3.7 🟡 `requirements.txt` is stale and inconsistent with `pyproject.toml`

| Package | `requirements.txt` | `pyproject.toml` |
|---|---|---|
| numpy | `>=1.24` | `>=1.26` |
| scipy | `>=1.10` | `>=1.12` |
| sgp4 | `>=2.23` | `>=2.22` |
| requests | present | absent (httpx used instead) |

Delete `requirements.txt` or auto-generate it:

```bash
echo "# GENERATED — do not edit manually" > requirements.txt
pip-compile pyproject.toml >> requirements.txt
```

---

## Part 4 — Test Gaps

### 4.1 🔴 No numerical validation of Foster Pc against a known value

Every test in `test_calculator.py` asserts only `result.pc >= 0.0`. A calculator that always returns `0.0` passes the entire suite.

**Add this test:**

```python
def test_foster_pc_known_value():
    """
    Head-on conjunction: b=[0,0], C=diag(1,1) km², HBR=0.02 km.
    Analytically: Pc = 1 - exp(-HBR²/(2*sigma²)) ≈ 2.0e-4
    """
    b = np.array([0.0, 0.0])
    C = np.diag([1.0, 1.0])
    calc = FosterPcCalculator(hard_body_radius_km=0.02)
    pc = calc.compute(b, C)
    assert abs(pc - 2.0e-4) / 2.0e-4 < 0.05   # within 5% of analytic value
```

---

### 4.2 🔴 No positive-definiteness assertion after Kalman update

`test_sensor_math.py` checks that trace shrinks but never checks:

```python
assert posterior_cov.is_positive_definite
```

---

### 4.3 🟠 SGP4 test uses a dummy state unrelated to the TLE

**File:** `tests/unit/test_sgp4.py`

SGP4 ignores the input state and propagates from its own TLE epoch. The test only checks shape. Add an altitude bounds check asserting the propagated position is within ISS bounds (380–430 km).

---

### 4.4 🟠 Monte Carlo test uses an invalid TLE string

**File:** `tests/unit/test_monte_carlo.py`

```python
TLERecord(line1="1 25544U", line2="2 25544", ...)   # not a valid TLE
```

The `sgp4` library silently fails on these strings. Mock the propagator with `MagicMock` instead.

---

### 4.5 🟠 CLI coverage tests assert only `exit_code == 0`

Most tests in `test_cli_coverage.py` patch `OUREContext` entirely and assert only that the CLI doesn't crash — not that it produces correct results. Add at least two end-to-end tests using a pre-computed CDM file that validate actual Pc output values.

---

### 4.6 🟡 No test that triggers `KeplerConvergenceError`

`kepler.py` raises `KeplerConvergenceError` on non-convergence but no test exercises this path. Pass `e=0.9999` with a near-parabolic mean anomaly and assert the exception is raised.

---

## Part 5 — Security

### 5.1 🔴 Credential copy to repo directory in `install.sh`

See §3.3. Highest-priority security fix.

### 5.2 🔴 Shell injection via `xargs` in credential export

See §3.3. Passwords with special characters can cause shell injection.

### 5.3 🟠 FastAPI CDM endpoint leaks internal exception messages

**File:** `oure/api/main.py`

```python
# Current — leaks internal paths and stack info
raise HTTPException(status_code=500, detail=f"Error processing CDM: {str(e)}")

# Fix
logger.exception("CDM processing failed")
raise HTTPException(
    status_code=500,
    detail="Failed to parse CDM file. Ensure it follows the CCSDS JSON schema."
)
```

### 5.4 🟠 NORAD IDs are not validated before URL construction

The CLI passes raw user input directly into the Space-Track API URL path. A malformed ID like `25544/format/tle` injects path segments.

**Fix:**

```python
import re

def validate_norad_id(sat_id: str) -> str:
    if not re.fullmatch(r"\d{1,9}", sat_id):
        raise click.BadParameter(f"Invalid NORAD ID: {sat_id!r}. Must be 1–9 digits.")
    return sat_id
```

---

## Part 6 — Ordered Action Plan

Do these in sequence. Each builds on the previous.

| # | Action | File(s) | Effort |
|---|---|---|---|
| 1 | Fix `ci.yml` branch trigger `main` → `master` | `.github/workflows/ci.yml` | 5 min |
| 2 | Add Foster Pc numerical validation test | `tests/unit/test_calculator.py` | 1 hr |
| 3 | Add `is_positive_definite` assert to sensor test | `tests/unit/test_sensor_math.py` | 15 min |
| 4 | Remove credential copy from `install.sh`; fix `xargs` export | `install.sh` | 30 min |
| 5 | Replace Euler J2 with secular drift rates | `oure/physics/j2_corrector.py` | 2 hr |
| 6 | Add warning + configurable default in `_default_covariance` | `oure/cli/utils.py` | 30 min |
| 7 | Replace bare Kepler loop with `solve_kepler_vectorized` | `oure/cli/utils.py` | 20 min |
| 8 | Extract `AtmosphericModel` class | `oure/physics/atmosphere.py` (new) | 1 hr |
| 9 | Fix `console` redefinition in `cmd_fetch.py` | `oure/cli/cmd_fetch.py` | 5 min |
| 10 | Fix B-plane projection to use full 6×6 covariance | `oure/risk/bplane.py` | 2 hr |
| 11 | Fix Foster series u=0 edge case | `oure/risk/foster.py` | 30 min |
| 12 | Add NORAD ID regex validator to CLI | `oure/cli/cmd_analyze.py` | 30 min |
| 13 | Harden FastAPI exception messages | `oure/api/main.py` | 20 min |
| 14 | Set `cov-fail-under=88` and wire live Codecov badge | `pyproject.toml`, `README.md` | 30 min |
| 15 | Delete or regenerate `requirements.txt` | `requirements.txt` | 15 min |
| 16 | Fix `mock_results.json` path in dashboard | `oure/dashboard/app.py` | 10 min |
| 17 | Fix Monte Carlo test to use a mock propagator | `tests/unit/test_monte_carlo.py` | 20 min |
| 18 | Add SGP4 altitude bounds assertion | `tests/unit/test_sgp4.py` | 15 min |
| 19 | Add `KeplerConvergenceError` trigger test | `tests/unit/test_physics.py` | 20 min |
| 20 | Add drag deceleration magnitude unit test | `tests/unit/test_drag.py` | 30 min |

---

## References

- Foster, J.L. & Estes, H.S. (1992). *A parametric analysis of orbital debris collision probability and maneuver rate for space vehicles.* NASA JSC-25898.
- Alfriend, K.T. & Akella, M.R. (2000). *Probability of collision error analysis.* Space Debris, 2(1).
- Vallado, D.A. (2013). *Fundamentals of Astrodynamics and Applications*, 4th ed. Microcosm Press.
- NASA (2016). *NASA Standard Breakup Model.* NASA SP-2016-593.
- Brouwer, D. (1959). *Solution of the problem of artificial satellite theory without drag.* Astronomical Journal, 64.
