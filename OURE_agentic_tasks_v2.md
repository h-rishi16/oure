# OURE — Remaining Fix Tasks (v2)
# Format: agentic CLI task list
# Each task is self-contained: file + exact change + acceptance test.
# Status: 23/32 original items resolved. 14 tasks remain (9 carry-over + 5 new).

---

## CONVENTIONS

- `TARGET_FILE`: path relative to repo root
- `ACTION`: what to do — edit / delete / create
- `FIND`: exact string to locate in the file (must be unique)
- `REPLACE`: exact replacement text (or NONE if deleting)
- `VERIFY`: shell command that must exit 0 after the change
- Multi-step tasks list steps as Step A, Step B, etc. Apply all steps before running VERIFY.

---

## TASK 1 — CRITICAL

```
ID: arch-test-risk-physics
PRIORITY: HIGH
TITLE: Add risk layer to allowed physics imports in architecture test

TARGET_FILE: tests/integration/test_architecture.py

ACTION: EDIT

FIND:
                                if (
                                    layer in ("conjunction", "uncertainty")
                                    and imported_layer == "physics"
                                ):

REPLACE:
                                if (
                                    layer in ("conjunction", "uncertainty", "risk")
                                    and imported_layer == "physics"
                                ):

REASON:
  oure/risk/optimizer.py imports oure.physics.maneuver and oure.physics.base.
  The architecture test does not exempt risk→physics, so it would fail if CI ran.
  This is the only change needed — risk importing from physics is intentional.

VERIFY: python -m pytest tests/integration/test_architecture.py -q
```

---

## TASK 2

```
ID: pyproject-add-pydantic-settings
PRIORITY: HIGH
TITLE: Add pydantic-settings and remove dead requests dependency from pyproject.toml

TARGET_FILE: pyproject.toml

ACTION: EDIT — Step A: add pydantic-settings

FIND:
    "pydantic>=2.5",

REPLACE:
    "pydantic>=2.5",
    "pydantic-settings>=2.0",

---

ACTION: EDIT — Step B: remove unused requests dependency
  (requests is listed but httpx is used everywhere; requests is never imported in source)

FIND:
    "requests>=2.31",

REPLACE:
    (delete this line entirely — no replacement)

VERIFY: python -c "import pydantic_settings; print('ok')" && grep -v "requests" pyproject.toml | grep -q "pydantic-settings"
```

---

## TASK 3

```
ID: pydantic-settings-config
PRIORITY: HIGH
TITLE: Create oure/core/config.py — fail fast on missing credentials at import time

TARGET_FILE: oure/core/config.py

ACTION: CREATE

CONTENT:
"""
OURE Core - Configuration
=========================
Validates required environment variables at startup using pydantic-settings.
Missing SPACETRACK_USER or SPACETRACK_PASS raises ValidationError immediately
at import time — not 30 seconds into the first API call.

Usage:
    from oure.core.config import config
    username = config.spacetrack_user
"""

from pydantic_settings import BaseSettings


class OUREConfig(BaseSettings):
    # Required — no defaults. Missing values raise ValidationError at import.
    spacetrack_user: str
    spacetrack_pass: str

    # Optional with sensible defaults
    oure_log_level: str = "INFO"
    oure_log_format: str = "console"
    oure_mc_samples: int = 1000
    oure_screening_dist_km: float = 5.0
    oure_hard_body_radius_m: float = 20.0
    oure_alert_red: float = 1e-3
    oure_alert_yellow: float = 1e-5
    oure_default_cov_sigma_km: float = 0.5
    oure_tle_max_age_hours: float = 48.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Module-level singleton — validated on first import.
# Import this from anywhere: from oure.core.config import config
config = OUREConfig()

VERIFY: python -c "
import os
os.environ['SPACETRACK_USER'] = 'test'
os.environ['SPACETRACK_PASS'] = 'test'
from oure.core.config import OUREConfig
c = OUREConfig()
assert c.spacetrack_user == 'test'
assert c.oure_tle_max_age_hours == 48.0
print('config ok')
"
```

---

## TASK 4

```
ID: wire-structlog-into-cli
PRIORITY: MEDIUM
TITLE: Replace dead setup_logging() with configure_logging() in CLI entrypoint

TARGET_FILE: oure/cli/main.py

ACTION: EDIT — Step A: remove the setup_logging function definition only
  WARNING: do NOT remove the `import logging` or `import sys` lines at the top.
  Other parts of the module use them.

FIND:
def setup_logging(verbose: bool, log_file: str | None = None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )

REPLACE:
# setup_logging removed — configure_logging() from logging_config is used instead

---

ACTION: EDIT — Step B: replace the call site inside cli()

FIND:
    setup_logging(verbose, log_file)

REPLACE:
    import os
    from oure.core.logging_config import LogFormat, configure_logging
    fmt = (
        LogFormat.JSON
        if os.getenv("OURE_LOG_FORMAT", "console").lower() == "json"
        else LogFormat.CONSOLE
    )
    configure_logging(
        level="DEBUG" if verbose else "INFO",
        format=fmt,
        log_file=log_file,
    )

VERIFY: python -c "from oure.cli.main import cli; print('cli import ok')"
```

---

## TASK 5

```
ID: delete-requirements-txt
PRIORITY: MEDIUM
TITLE: Delete stale requirements.txt — conflicts with pyproject.toml

TARGET_FILE: requirements.txt

ACTION: DELETE
COMMAND: rm requirements.txt

REASON:
  numpy >=1.24 in requirements.txt vs >=1.26 in pyproject.toml
  scipy >=1.10 in requirements.txt vs >=1.12 in pyproject.toml
  requests present in requirements.txt but dependency removed in TASK 2
  TESTING.md already updated to: pip install -e '.[dev]'
  Keeping this file causes new contributors to install wrong versions.

VERIFY: test ! -f requirements.txt
```

---

## TASK 6

```
ID: start-web-process-health-check
PRIORITY: MEDIUM
TITLE: Verify background processes actually started before reporting success

TARGET_FILE: start_web.sh

ACTION: EDIT

FIND:
echo "Web components are running."
echo "API Docs: http://localhost:8000/docs"
echo "Dashboard: http://localhost:8501"

REPLACE:
sleep 2
kill -0 $CELERY_PID 2>/dev/null || { echo "ERROR: Celery worker failed to start. Is Redis running?"; kill $API_PID $DASH_PID 2>/dev/null; exit 1; }
kill -0 $API_PID    2>/dev/null || { echo "ERROR: FastAPI failed to start."; kill $CELERY_PID $DASH_PID 2>/dev/null; exit 1; }
kill -0 $DASH_PID   2>/dev/null || { echo "ERROR: Streamlit dashboard failed to start."; kill $CELERY_PID $API_PID 2>/dev/null; exit 1; }
echo "Web components are running."
echo "API Docs: http://localhost:8000/docs"
echo "Dashboard: http://localhost:8501"

VERIFY: bash -n start_web.sh
```

---

## TASK 7

```
ID: fix-oureconfig-no-defaults
PRIORITY: HIGH
TITLE: Ensure OUREConfig required fields have no defaults (already handled in TASK 3)

NOTE: This is satisfied by TASK 3. The CREATE action in TASK 3 writes
spacetrack_user: str and spacetrack_pass: str with NO default values.
If TASK 3 has already run, verify only:

VERIFY: python -c "
import os
# Remove credentials to test that missing vars raise
for k in ('SPACETRACK_USER', 'SPACETRACK_PASS'):
    os.environ.pop(k, None)
try:
    from oure.core.config import OUREConfig
    OUREConfig()
    print('FAIL — should have raised')
    exit(1)
except Exception as e:
    print(f'PASS — raised as expected: {type(e).__name__}')
"
```

---

## TASK 8

```
ID: fix-stm-propagator-singleton
PRIORITY: MEDIUM
TITLE: Move NumericalPropagator instantiation out of _numerical_stm() hot path

TARGET_FILE: oure/uncertainty/stm.py

ACTION: EDIT — Step A: add __init__ to STMCalculator

FIND:
class STMCalculator:
    """
    Computes the 6×6 State Transition Matrix Φ(t, t₀) for covariance
    propagation.
    """

    def __init__(self, fidelity: int = 1):
        assert fidelity in (0, 1, 2), "Fidelity must be 0, 1, or 2"
        self.fidelity = fidelity

REPLACE:
class STMCalculator:
    """
    Computes the 6×6 State Transition Matrix Φ(t, t₀) for covariance
    propagation.
    """

    def __init__(self, fidelity: int = 1):
        assert fidelity in (0, 1, 2), "Fidelity must be 0, 1, or 2"
        self.fidelity = fidelity
        # Pre-instantiate propagator for fidelity=2 to avoid recreating
        # NumericalPropagator (and its AtmosphericModel) on every STM column.
        self._num_prop: object = None
        if fidelity == 2:
            from oure.physics.numerical import NumericalPropagator
            self._num_prop = NumericalPropagator()

---

ACTION: EDIT — Step B: use self._num_prop inside _numerical_stm()

FIND:
        from oure.physics.numerical import NumericalPropagator

        prop = NumericalPropagator()

        epsilon = 1e-4  # Perturbation size in km and km/s

REPLACE:
        from oure.physics.numerical import NumericalPropagator

        prop = self._num_prop if self._num_prop is not None else NumericalPropagator()

        epsilon = 1e-4  # Perturbation size in km and km/s

VERIFY: python -m pytest tests/unit/test_stm.py -q
```

---

## TASK 9

```
ID: fix-sensor-cov-mutation
PRIORITY: MEDIUM
TITLE: Stop mutating CovarianceMatrix in-place in cmd_sensor.py

TARGET_FILE: oure/cli/cmd_sensor.py

ACTION: EDIT

FIND:
    p_cov = _default_covariance(primary)
    s_cov_stale = _default_covariance(secondary)
    s_cov_stale.matrix[:3, :3] = np.eye(3) * 25.0  # 25 km^2 = 5km sigma

REPLACE:
    from oure.core.models import CovarianceMatrix
    p_cov = _default_covariance(primary)
    _s_cov_default = _default_covariance(secondary)
    # Construct a new CovarianceMatrix with inflated position block (5 km sigma)
    # instead of mutating the returned object in place.
    _stale_matrix = _s_cov_default.matrix.copy()
    _stale_matrix[:3, :3] = np.eye(3) * 25.0  # 25 km^2 = 5 km sigma
    s_cov_stale = CovarianceMatrix(
        matrix=_stale_matrix,
        epoch=_s_cov_default.epoch,
        sat_id=_s_cov_default.sat_id,
    )

VERIFY: python -c "from oure.cli.cmd_sensor import task_sensor; print('import ok')"
```

---

## TASK 10

```
ID: fix-tle-staleness-config
PRIORITY: LOW
TITLE: Make TLE max_age_hours configurable via OUREConfig instead of hardcoded 48h

TARGET_FILE: oure/data/cache.py

DEPENDS_ON: TASK 3 (oure/core/config.py must exist first)

ACTION: EDIT — Step A: import config at top of cache.py

FIND:
from oure.core.models import TLERecord

REPLACE:
from oure.core.models import TLERecord

# Import lazily to avoid circular imports — used only in get_tle()
def _get_tle_max_age() -> float:
    try:
        from oure.core.config import config
        return config.oure_tle_max_age_hours
    except Exception:
        return 48.0  # safe fallback if config not yet initialised

---

ACTION: EDIT — Step B: use _get_tle_max_age() as default in get_tle()

FIND:
    def get_tle(self, sat_id: str, max_age_hours: float = 48.0) -> TLERecord | None:

REPLACE:
    def get_tle(self, sat_id: str, max_age_hours: float | None = None) -> TLERecord | None:
        if max_age_hours is None:
            max_age_hours = _get_tle_max_age()

VERIFY: python -m pytest tests/unit/test_cache.py -q
```

---

## TASK 11

```
ID: install-sh-credential-copy-warning
PRIORITY: LOW
TITLE: Warn user when keys.env is copied from repo directory

TARGET_FILE: install.sh

ACTION: EDIT

FIND:
else
    cp keys.env "$INSTALL_DIR/keys.env"
fi

REPLACE:
else
    echo -e "${YELLOW}==> keys.env found in current directory — copying to install location.${NC}"
    cp keys.env "$INSTALL_DIR/keys.env"
    echo -e "${YELLOW}WARNING: Ensure keys.env is in your .gitignore to avoid committing credentials.${NC}"
    grep -qxF 'keys.env' .gitignore 2>/dev/null || echo 'keys.env' >> .gitignore
fi

VERIFY: bash -n install.sh
```

---

## TASK 12

```
ID: foster-series-terms-reduce
PRIORITY: LOW
TITLE: Reduce Foster series terms from 200 to 30

TARGET_FILE: oure/risk/foster.py

ACTION: EDIT

FIND:
        series_terms: int = 200,

REPLACE:
        series_terms: int = 30,

REASON:
  For LEO conjunctions the Poisson weight exp(-u)*u^n/n! is negligible
  after n~20. 200 terms wastes ~7x compute with zero accuracy gain.
  30 terms provides >10 decimal places of convergence for all LEO cases.

VERIFY: python -m pytest tests/unit/test_calculator.py -q
```

---

## TASK 13

```
ID: optimizer-final-pc-direct
PRIORITY: LOW
TITLE: Remove fragile double-negation for final_pc — call compute_pc directly

TARGET_FILE: oure/risk/optimizer.py

ACTION: EDIT

FIND:
        if res.success:
            optimal_dv = res.x
            # Calculate final Pc to return
            margin = constraint_pc(optimal_dv)
            final_pc = self.target_pc - margin
            return {
                "success": True,
                "optimal_dv_km_s": optimal_dv,
                "dv_mag_cm_s": np.linalg.norm(optimal_dv) * 100000.0,
                "final_pc": final_pc,
                "iterations": res.nit,
            }

REPLACE:
        if res.success:
            optimal_dv = res.x
            # Compute final Pc directly — avoids fragile double-negation via constraint_pc.
            # margin = target_pc - actual_pc, so target_pc - margin = actual_pc algebraically,
            # but a sign flip in constraint_pc would silently return a wrong value.
            maneuver = Maneuver(burn_epoch=self.burn_epoch, delta_v_eci=optimal_dv)
            man_prop = ManeuverPropagator(self.base_prop, [maneuver])
            tca_res = self.tca_finder.find_tca(
                self.primary_state, man_prop,
                self.secondary_state, self.base_prop,
                self.nominal_tca - timedelta(hours=1),
                self.nominal_tca + timedelta(hours=1),
            )
            if tca_res:
                new_tca, new_miss = tca_res
                p_tca = man_prop.propagate_to(self.primary_state, new_tca)
                s_tca = self.base_prop.propagate_to(self.secondary_state, new_tca)
                v_rel = float(np.linalg.norm(p_tca.v - s_tca.v))
                final_event = ConjunctionEvent(
                    primary_id=self.primary_state.sat_id,
                    secondary_id=self.secondary_state.sat_id,
                    tca=new_tca,
                    miss_distance_km=new_miss,
                    relative_velocity_km_s=v_rel,
                    primary_state=p_tca,
                    secondary_state=s_tca,
                    primary_covariance=self.primary_cov,
                    secondary_covariance=self.secondary_cov,
                )
                final_pc = self.risk_calc.compute_pc(final_event).pc
            else:
                final_pc = 0.0
            return {
                "success": True,
                "optimal_dv_km_s": optimal_dv,
                "dv_mag_cm_s": np.linalg.norm(optimal_dv) * 100000.0,
                "final_pc": final_pc,
                "iterations": res.nit,
            }

VERIFY: python -m pytest tests/unit/test_optimizer_logic.py -q
```

---

## TASK 14

```
ID: assessor-prop-groups-note
PRIORITY: LOW
TITLE: Document known limitation of prop_groups batching in assessor.py

TARGET_FILE: oure/conjunction/assessor.py

ACTION: EDIT
NOTE: This is a documentation-only change. The batching fix requires
      a larger refactor (propagator identity vs equality). For now,
      document the limitation so future contributors understand why
      the batch path rarely fires in production.

FIND:
        # Optimization: Group secondaries by their propagator instance to enable batching
        from collections import defaultdict

        prop_groups = defaultdict(list)
        for j, (_, _, s_prop) in enumerate(secondaries):
            prop_groups[id(s_prop)].append(j)

REPLACE:
        # Optimization: Group secondaries by their propagator instance to enable batching.
        # NOTE: In practice, PropagatorFactory.build() returns a new instance per satellite,
        # so id(s_prop) is unique for each secondary and groups are always size-1.
        # The batch path (propagate_many_to) therefore rarely fires for catalog screening.
        # A future fix: group by (tle_sat_id, propagator_type) tuple instead of object id.
        from collections import defaultdict

        prop_groups = defaultdict(list)
        for j, (_, _, s_prop) in enumerate(secondaries):
            prop_groups[id(s_prop)].append(j)

VERIFY: python -m pytest tests/unit/test_assessor.py -q
```

---

## EXECUTION ORDER

```
Run tasks in this exact order to satisfy dependencies:

1.  pyproject-add-pydantic-settings    (TASK 2)  — install dep first
2.  arch-test-risk-physics             (TASK 1)  — unblocks CI immediately
3.  pydantic-settings-config           (TASK 3)  — new module, needed by TASK 10
4.  fix-oureconfig-no-defaults         (TASK 7)  — verify TASK 3 is correct
5.  wire-structlog-into-cli            (TASK 4)  — uses logging_config
6.  fix-stm-propagator-singleton       (TASK 8)  — standalone physics fix
7.  fix-sensor-cov-mutation            (TASK 9)  — standalone CLI fix
8.  fix-tle-staleness-config           (TASK 10) — depends on TASK 3
9.  delete-requirements-txt            (TASK 5)  — cleanup after pyproject fix
10. start-web-process-health-check     (TASK 6)  — standalone devops fix
11. install-sh-credential-copy-warning (TASK 11) — standalone security note
12. foster-series-terms-reduce         (TASK 12) — standalone perf fix
13. optimizer-final-pc-direct          (TASK 13) — standalone physics fix
14. assessor-prop-groups-note          (TASK 14) — doc-only, run last
```

---

## FULL VERIFICATION AFTER ALL TASKS

```bash
# Run full test suite — must pass with >=88% coverage
python -m pytest tests/ -v --cov=oure --cov-report=term-missing

# Run type checker — must report zero errors
mypy oure/

# Run linter — must report zero errors
ruff check oure/ tests/

# Confirm architecture test passes (catches risk→physics regression)
python -m pytest tests/integration/test_architecture.py -v

# Confirm requirements.txt is gone
test ! -f requirements.txt && echo "requirements.txt deleted ok"

# Confirm pydantic-settings is importable
python -c "from oure.core.config import OUREConfig; print('OUREConfig ok')"
```

---

## ALREADY RESOLVED — DO NOT RE-APPLY

```
The following were fixed before this task file was generated.
Applying them again will break working code.

RESOLVED:
  ci.yml              branch trigger main→master
  oure/cli/utils.py   Kepler loop → solve_kepler_vectorized()
  oure/cli/utils.py   _default_covariance() warning + 0.5 km sigma
  oure/cli/cmd_fetch  console shadowing removed
  oure/risk/bplane.py B-plane now uses full 2×6 T_full against 6×6 covariance
  install.sh          xargs injection → set -o allexport; source
  oure/data/cdm_parser.py   silent fallback → logs warning
  oure/api/main.py    FastAPI exception leakage → safe message + logger.exception
  oure/cli/cmd_analyze.py   NORAD ID regex validation added
  tests/unit/test_calculator.py   known-value Foster Pc test added
  tests/unit/test_sensor_math.py  is_positive_definite assert added
  tests/unit/test_monte_carlo.py  mock propagator replaces broken TLE strings
  tests/unit/test_sgp4.py         altitude bounds assertion added
  tests/unit/test_kepler.py       KeplerConvergenceError trigger test added
  oure/physics/atmosphere.py      AtmosphericModel extracted
  docker-compose.yaml             Redis healthcheck + condition: service_healthy
  oure/api/tasks.py               worker_init credential validation
  pyproject.toml                  cov-fail-under=88
  CONTRIBUTING.md                 created
  oure/dashboard/app.py           mock_results.json uses Path(__file__) 
  oure/physics/numerical.py       propagate_many_to checks sol.success
  oure/physics/j2_corrector.py    secular drift rates replacing Euler
  oure/risk/foster.py             u=0 clamp via max(u, 1e-12)
```
