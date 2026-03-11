**OURE**

Orbital Uncertainty & Risk Engine

**Agentic Build Specification**

*Complete architecture, file tree, class contracts, math derivations,*

*agent task sequences, and professional standards reference*

  ------------------------------- ---------------------------------------
  **Version**                     1.0.0 (Initial Release)

  **Language**                    Python 3.11+

  **Standard**                    PEP 8 + PEP 517 + Google Docstrings

  **Target Agent**                Claude Code / GPT-Engineer / Aider
  ------------------------------- ---------------------------------------

+-----------------------------------------------------------------------+
| **§1 Agent Execution Protocol**                                       |
|                                                                       |
| *How a coding agent must read and execute this specification*         |
+-----------------------------------------------------------------------+

**1.1 How to Read This Document**

This specification is written for an autonomous coding agent. Every
section contains self-contained, actionable instructions. The agent
must:

1.  Read §2 (Project Manifest) first --- it defines all paths, names,
    and conventions used everywhere else.

2.  Execute §3 (Bootstrap) to scaffold the project skeleton in one pass
    before writing any module code.

3.  Implement modules in the dependency order defined in §5 (Module
    Dependency Graph). Never implement a consumer before its dependency.

4.  After each module: run the validation gate defined in §9 (Quality
    Gates). Only advance on a green gate.

5.  Complete §8 (Test Suite) as the final step before the project is
    considered done.

+---+-------------------------------------------------------------------+
| * | **Atomic Tasks**                                                  |
| * |                                                                   |
| ⚡ | Each subsection marked with a ▸ task bullet is one atomic agent  |
| * | action. The agent must complete the action fully before moving to |
| * | the next. Partial completion is not acceptable --- all specified  |
|   | methods, docstrings, type annotations, and tests must be present. |
+---+-------------------------------------------------------------------+

**1.2 Conventions Used in This Document**

  -----------------------------------------------------------------------------
  **Symbol**          **Meaning**
  ------------------- ---------------------------------------------------------
  **monospace**       Exact file path, class name, method name, or shell
                      command --- copy verbatim

  **→**               Produces / returns

  **::=**             Is defined as

  **\[REQUIRED\]**    The agent must implement this --- no omissions

  **\[OPTIONAL\]**    Implement if time permits --- mark TODO otherwise

  **\[AGENT-GEN\]**   Generate the full implementation from the spec --- no
                      stubs

  **«interface»**     Abstract base class --- never instantiate directly
  -----------------------------------------------------------------------------

**1.3 Non-Negotiable Standards**

+---+-------------------------------------------------------------------+
| * | **Hard Rules --- Violations Fail the Build**                      |
| * |                                                                   |
| 🔒 | The following rules are enforced by the CI pipeline. Any agent   |
| * | output that violates them must be regenerated.                    |
| * |                                                                   |
+---+-------------------------------------------------------------------+

-   Every public function, method, and class MUST have a Google-style
    docstring with Args:, Returns:, and Raises: sections.

-   Every function signature MUST have complete PEP 484 type annotations
    --- no bare \`def foo(x)\` signatures.

-   No magic numbers in physics code --- every constant must be a named
    module-level variable with units in the name (e.g., \`MU_KM3_S2\`,
    \`R_EARTH_KM\`).

-   No cross-layer imports: \`physics\` never imports \`data\`, \`cli\`
    never imports \`physics\` directly (only through \`core\`).

-   Test coverage must be \>= 80% on all non-CLI modules. Use \`pytest
    \--cov\` to verify.

-   All external API calls must go through the \`data.fetchers\` layer
    --- never call \`requests\` from physics or risk modules.

+-----------------------------------------------------------------------+
| **§2 Project Manifest**                                               |
|                                                                       |
| *Canonical names, paths, versions, and configuration values*          |
+-----------------------------------------------------------------------+

**2.1 Identity**

  -----------------------------------------------------------------------
  **Key**                 **Value**
  ----------------------- -----------------------------------------------
  **Package name**        oure

  **PyPI slug**           oure-risk-engine

  **CLI entry point**     oure

  **Python minimum**      3.11

  **License**             MIT

  **Top-level namespace** Single: \`oure\`
  -----------------------------------------------------------------------

**2.2 Full File Tree**

The agent must create every file listed here. Files marked \[AGENT-GEN\]
require full implementation. Files marked \[CONFIG\] are
configuration/data files with exact content specified in §3.

  -----------------------------------------------------------------------
  📄 **oure/ (project root)**

  \# ── Python package ─────────────────────────────────────────────

  oure/

  \_\_init\_\_.py \[AGENT-GEN\] package init + \_\_version\_\_

  py.typed \[CONFIG\] PEP 561 marker (empty file)

  core/

  \_\_init\_\_.py

  models.py \[AGENT-GEN\] ALL frozen dataclasses

  constants.py \[AGENT-GEN\] ALL physics constants

  exceptions.py \[AGENT-GEN\] ALL custom exceptions

  logging_config.py \[AGENT-GEN\] structured logging setup

  data/

  \_\_init\_\_.py

  base.py \[AGENT-GEN\] BaseDataFetcher ABC

  cache.py \[AGENT-GEN\] CacheManager (SQLite)

  spacetrack.py \[AGENT-GEN\] SpaceTrackFetcher

  noaa.py \[AGENT-GEN\] NOAASolarFluxFetcher

  schemas.py \[AGENT-GEN\] Pydantic validation schemas

  physics/

  \_\_init\_\_.py

  base.py \[AGENT-GEN\] BasePropagator ABC

  sgp4_propagator.py \[AGENT-GEN\] SGP4Propagator

  j2_corrector.py \[AGENT-GEN\] J2PerturbationCorrector

  drag_corrector.py \[AGENT-GEN\] AtmosphericDragCorrector

  factory.py \[AGENT-GEN\] PropagatorFactory

  kepler.py \[AGENT-GEN\] Kepler equation solvers

  frames.py \[AGENT-GEN\] Coordinate frame transforms

  uncertainty/

  \_\_init\_\_.py

  stm.py \[AGENT-GEN\] STMCalculator (3 fidelity levels)

  covariance_propagator.py \[AGENT-GEN\] CovariancePropagator

  monte_carlo.py \[AGENT-GEN\] MonteCarloUncertaintyPropagator

  noise.py \[AGENT-GEN\] ProcessNoiseModel

  conjunction/

  \_\_init\_\_.py

  spatial_index.py \[AGENT-GEN\] KDTreeSpatialIndex

  tca_finder.py \[AGENT-GEN\] TCARefinementEngine

  assessor.py \[AGENT-GEN\] ConjunctionAssessor (orchestrator)

  risk/

  \_\_init\_\_.py

  bplane.py \[AGENT-GEN\] BPlaneProjector

  foster.py \[AGENT-GEN\] FosterPcCalculator

  calculator.py \[AGENT-GEN\] RiskCalculator (orchestrator)

  alert.py \[AGENT-GEN\] AlertClassifier

  cli/

  \_\_init\_\_.py

  main.py \[AGENT-GEN\] click group + global opts

  cmd_fetch.py \[AGENT-GEN\] \`oure fetch\` subcommand

  cmd_analyze.py \[AGENT-GEN\] \`oure analyze\` subcommand

  cmd_monitor.py \[AGENT-GEN\] \`oure monitor\` subcommand

  cmd_cache.py \[AGENT-GEN\] \`oure cache\` subcommand

  cmd_report.py \[AGENT-GEN\] \`oure report\` subcommand

  formatters.py \[AGENT-GEN\] Rich console output helpers

  progress.py \[AGENT-GEN\] Rich progress bar wrappers

  \# ── Tests ────────────────────────────────────────────────────────

  tests/

  conftest.py \[AGENT-GEN\] fixtures + fake data factories

  unit/

  test_models.py

  test_constants.py

  test_kepler.py

  test_frames.py

  test_sgp4.py

  test_j2.py

  test_drag.py

  test_stm.py

  test_covariance.py

  test_monte_carlo.py

  test_spatial_index.py

  test_tca_finder.py

  test_bplane.py

  test_foster.py

  test_cache.py

  integration/

  test_pipeline_full.py

  test_cli_fetch.py

  test_cli_analyze.py

  fixtures/

  sample_tles.json

  sample_covariances.json

  expected_pc_results.json

  \# ── Configuration files ──────────────────────────────────────────

  pyproject.toml \[CONFIG\] full content in §3.1

  .pre-commit-config.yaml \[CONFIG\] full content in §3.2

  .github/workflows/ci.yml \[CONFIG\] full content in §3.3

  Makefile \[CONFIG\] full content in §3.4

  README.md \[AGENT-GEN\]

  CHANGELOG.md \[CONFIG\]

  .env.example \[CONFIG\]

  .gitignore \[CONFIG\]

  docs/ \[OPTIONAL\]

  -----------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§3 Bootstrap & Configuration**                                      |
|                                                                       |
| *Exact content for all configuration files*                           |
+-----------------------------------------------------------------------+

**3.1 pyproject.toml --- Complete Content**

+---+-------------------------------------------------------------------+
| * | **Agent Task**                                                    |
| * |                                                                   |
| 📋 | Create \`pyproject.toml\` at the project root with exactly the   |
| * | following content. Do not omit any section.                       |
| * |                                                                   |
+---+-------------------------------------------------------------------+

  -------------------------------------------------------------------------------
  📄 **pyproject.toml**

  \[build-system\]

  requires = \[\"hatchling\"\]

  build-backend = \"hatchling.build\"

  \[project\]

  name = \"oure-risk-engine\"

  version = \"1.0.0\"

  description = \"Orbital Uncertainty & Risk Engine --- Satellite Collision
  Probability Solver\"

  readme = \"README.md\"

  license = { text = \"MIT\" }

  requires-python = \"\>=3.11\"

  dependencies = \[

  \"click\>=8.1\",

  \"numpy\>=1.26\",

  \"scipy\>=1.12\",

  \"sgp4\>=2.22\",

  \"requests\>=2.31\",

  \"pydantic\>=2.5\",

  \"rich\>=13.7\",

  \"structlog\>=24.1\",

  \"tenacity\>=8.2\",

  \"httpx\>=0.27\",

  \]

  \[project.optional-dependencies\]

  dev = \[\"pytest\>=8\", \"pytest-cov\", \"pytest-asyncio\", \"hypothesis\",

  \"ruff\", \"mypy\", \"pre-commit\", \"faker\"\]

  vis = \[\"matplotlib\>=3.8\", \"plotly\>=5.18\"\]

  \[project.scripts\]

  oure = \"oure.cli.main:cli\"

  \[tool.ruff\]

  line-length = 100

  target-version = \"py311\"

  select =
  \[\"E\",\"F\",\"W\",\"I\",\"N\",\"UP\",\"ANN\",\"B\",\"C4\",\"SIM\",\"TCH\"\]

  ignore = \[\"ANN101\",\"ANN102\"\]

  \[tool.mypy\]

  python_version = \"3.11\"

  strict = true

  ignore_missing_imports = true

  \[tool.pytest.ini_options\]

  testpaths = \[\"tests\"\]

  addopts = \"\--cov=oure \--cov-report=term-missing \--cov-fail-under=80\"

  \[tool.coverage.run\]

  omit = \[\"oure/cli/\*\", \"tests/\*\"\]

  -------------------------------------------------------------------------------

**3.2 Makefile --- Developer Workflow**

  -----------------------------------------------------------------------
  📄 **Makefile**

  \# OURE Developer Workflow

  .PHONY: install dev lint type test build clean

  install:

  pip install -e .

  dev:

  pip install -e \'.\[dev,vis\]\'

  pre-commit install

  lint:

  ruff check oure/ tests/

  ruff format \--check oure/ tests/

  type:

  mypy oure/

  test:

  pytest tests/unit/ -v

  test-all:

  pytest tests/ -v

  build:

  python -m build

  clean:

  find . -type d -name \_\_pycache\_\_ -exec rm -rf {} +

  rm -rf .mypy_cache .pytest_cache dist build

  -----------------------------------------------------------------------

**3.3 .env.example**

  -----------------------------------------------------------------------
  📄 **.env.example**

  \# Space-Track.org credentials

  SPACETRACK_USER=your@email.com

  SPACETRACK_PASS=your_password

  \# OURE configuration

  OURE_CACHE_DB=\~/.oure/cache.db

  OURE_LOG_LEVEL=INFO

  OURE_LOG_FORMAT=json \# json \| console

  OURE_MC_SAMPLES=1000

  OURE_SCREENING_DIST_KM=5.0

  OURE_HARD_BODY_RADIUS_M=20.0

  \# Alert thresholds

  OURE_ALERT_RED=1e-3

  OURE_ALERT_YELLOW=1e-5

  -----------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§4 Core Layer**                                                     |
|                                                                       |
| *Shared data models, constants, and exceptions --- the foundation     |
| everything else imports*                                              |
+-----------------------------------------------------------------------+

**4.1 core/constants.py**

+---+-------------------------------------------------------------------+
| * | **Agent Task \[AGENT-GEN\]**                                      |
| * |                                                                   |
| 📋 | Implement all physical constants as module-level typed variables. |
| * | Every constant must include units in its name and a docstring     |
| * | comment. Group by physical domain.                                |
+---+-------------------------------------------------------------------+

  -----------------------------------------------------------------------
  📄 **oure/core/constants.py**

  \"\"\"Physical and orbital mechanics constants used throughout
  OURE.\"\"\"

  \# ── Gravitational ────────────────────────────────────────────────

  MU_KM3_S2: float = 398600.4418

  \"\"\"Standard gravitational parameter of Earth (km³/s²).\"\"\"

  MU_M3_S2: float = 3.986004418e14

  \"\"\"Standard gravitational parameter of Earth (m³/s²).\"\"\"

  \# ── Earth Geometry ───────────────────────────────────────────────

  R_EARTH_KM: float = 6378.137

  \"\"\"WGS84 equatorial radius of Earth (km).\"\"\"

  R_EARTH_M: float = 6378137.0

  \"\"\"WGS84 equatorial radius of Earth (m).\"\"\"

  F_OBLATE: float = 1.0 / 298.257223563

  \"\"\"WGS84 flattening factor (dimensionless).\"\"\"

  \# ── Zonal Harmonics ──────────────────────────────────────────────

  J2: float = 1.08262668e-3

  \"\"\"Second zonal harmonic --- Earth oblateness (dimensionless).\"\"\"

  J3: float = -2.53265648e-6

  \"\"\"Third zonal harmonic (dimensionless).\"\"\"

  J4: float = -1.61962159e-6

  \"\"\"Fourth zonal harmonic (dimensionless).\"\"\"

  \# ── Rotation ─────────────────────────────────────────────────────

  OMEGA_EARTH_RAD_S: float = 7.2921150e-5

  \"\"\"Earth sidereal rotation rate (rad/s).\"\"\"

  \# ── Atmosphere ───────────────────────────────────────────────────

  SOLAR_FLUX_MEAN_SFU: float = 150.0

  \"\"\"Long-term mean F10.7 solar flux (Solar Flux Units).\"\"\"

  JACCHIA_SOLAR_COUPLING: float = 0.003

  \"\"\"Empirical solar flux density coupling constant (1/SFU).\"\"\"

  \# ── Time ─────────────────────────────────────────────────────────

  SECONDS_PER_DAY: float = 86400.0

  SECONDS_PER_MINUTE: float = 60.0

  TWO_PI: float = 6.283185307179586

  -----------------------------------------------------------------------

**4.2 core/models.py --- All Dataclasses**

+---+-------------------------------------------------------------------+
| * | **Agent Task \[AGENT-GEN\]**                                      |
| * |                                                                   |
| 📋 | Implement all dataclasses with frozen=True where specified,      |
| * | \_\_post_init\_\_ validation, and complete properties. Import     |
| * | numpy for array fields.                                           |
+---+-------------------------------------------------------------------+

  ----------------------------------------------------------------------------------------
  **Class**              **Frozen**   **Key Fields**                 **Purpose**
  ---------------------- ------------ ------------------------------ ---------------------
  **StateVector**        Yes          r: ndarray(3), v: ndarray(3),  ECI position+velocity
                                      epoch: datetime, sat_id: str   at one epoch

  **TLERecord**          Yes          sat_id, name, line1, line2,    Raw TLE as fetched
                                      epoch, bstar, mean_motion,     from Space-Track
                                      \...                           

  **CovarianceMatrix**   No           matrix: ndarray(6,6), epoch,   6×6 P matrix with
                                      sat_id, frame=\'ECI\'          helpers

  **SolarFluxData**      Yes          date, f10_7, f10_7_81d_avg,    NOAA F10.7 and Ap
                                      ap_index                       index

  **AtmosphereParams**   Yes          f10_7, ap_index, rho_ref,      Instantaneous
                                      scale_height_km                atmosphere model

  **ConjunctionEvent**   No           primary_id, secondary_id, tca, One close approach
                                      miss_km, v_rel_km_s, states,   event
                                      covs                           

  **BPlaneProjection**   No           xi_hat, zeta_hat,              B-plane coordinate
                                      T_matrix(2×3), b_vec_2d,       system
                                      C_2d(2×2)                      

  **RiskResult**         No           conjunction, pc,               Final Pc output
                                      warning_level, C_combined,     
                                      method, n_mc                   

  **CacheEntry**         Yes          key, value_json, fetched_at,   SQLite cache record
                                      ttl_s                          

  **PipelineConfig**     No           mc_samples, screening_km,      Runtime configuration
                                      hbr_m, look_ahead_h, fidelity  bundle
  ----------------------------------------------------------------------------------------

**4.2.1 StateVector --- Full Spec**

  -----------------------------------------------------------------------
  📄 **StateVector contract**

  class StateVector:

  \# Fields

  r: np.ndarray \# ECI position (km), shape (3,)

  v: np.ndarray \# ECI velocity (km/s), shape (3,)

  epoch: datetime \# UTC epoch

  sat_id: str \# NORAD catalog ID string

  \# \_\_post_init\_\_ must enforce:

  \# r.shape == (3,) and v.shape == (3,)

  \# Both arrays are float64

  \# Properties (computed, no storage)

  \@property speed_km_s() -\> float \# \|v\|

  \@property altitude_km() -\> float \# \|r\| - R_EARTH_KM

  \@property state_vector_6d() -\> ndarray \# concat(\[r, v\]), shape
  (6,)

  \@property is_in_leo() -\> bool \# altitude \< 2000 km

  \@property orbital_energy() -\> float \# -mu/(2a) in km²/s²

  \# Class methods

  \@classmethod from_6d(vec: ndarray, epoch, sat_id) -\> StateVector

  \@classmethod from_dict(d: dict) -\> StateVector

  def to_dict() -\> dict

  def \_\_repr\_\_() -\> str \# human-readable summary

  -----------------------------------------------------------------------

**4.3 core/exceptions.py**

  -----------------------------------------------------------------------
  📄 **oure/core/exceptions.py**

  \"\"\"All OURE custom exceptions in one place.\"\"\"

  class OUREBaseError(Exception):

  \"\"\"Root exception. Never raise directly.\"\"\"

  class PropagationError(OUREBaseError):

  \"\"\"Raised when an orbit propagation fails to converge.\"\"\"

  class KeplerConvergenceError(PropagationError):

  \"\"\"Raised when Kepler equation Newton-Raphson fails.\"\"\"

  class CovarianceError(OUREBaseError):

  \"\"\"Raised when a covariance matrix is invalid.\"\"\"

  class CovarianceNotPositiveDefiniteError(CovarianceError):

  \"\"\"Raised when Cholesky decomposition fails.\"\"\"

  class DataFetchError(OUREBaseError):

  \"\"\"Raised when an external API fetch fails.\"\"\"

  class SpaceTrackAuthError(DataFetchError):

  \"\"\"Raised when Space-Track login is rejected.\"\"\"

  class CacheError(OUREBaseError):

  \"\"\"Raised on SQLite cache read/write failure.\"\"\"

  class ConjunctionAssessmentError(OUREBaseError):

  \"\"\"Raised when conjunction screening fails.\"\"\"

  class BPlaneError(OUREBaseError):

  \"\"\"Raised when B-plane construction fails (e.g. degenerate
  geometry).\"\"\"

  class AlertThresholdError(OUREBaseError):

  \"\"\"Raised on invalid alert configuration.\"\"\"

  -----------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§5 Module Dependency Graph**                                        |
|                                                                       |
| *Implementation order and import rules for the agent*                 |
+-----------------------------------------------------------------------+

**5.1 Dependency Order**

+---+-------------------------------------------------------------------+
| * | **Critical for Agent**                                            |
| * |                                                                   |
| ⚡ | The agent must implement modules in the order below. Layer N may |
| * | only import from layers 1..N-1. Any violation causes a circular   |
| * | import that will fail at runtime.                                 |
+---+-------------------------------------------------------------------+

  -------------------------------------------------------------------------------------------------
  **Layer**       **Modules**                              **May Import From** **Must NOT Import
                                                                               From**
  --------------- ---------------------------------------- ------------------- --------------------
  **1 --- Core**  core.constants\`, \`core.exceptions      stdlib only         Everything

  **2 ---         core.models                              Layer 1 + \`numpy\` data, physics,
  Models**                                                                     uncertainty, risk,
                                                                               cli

  **3 --- Data**  data.base\`, \`data.cache\`,             Layers 1-2 +        physics,
                  \`data.schemas                           \`pydantic\`,       uncertainty, risk,
                                                           \`sqlite3\`         cli

  **4 --- Data    data.spacetrack\`, \`data.noaa           Layers 1-3 +        physics,
  IO**                                                     \`requests\`,       uncertainty, risk,
                                                           \`httpx\`           cli

  **5 ---         physics.base\`, \`physics.kepler\`,      Layers 1-2 +        data, uncertainty,
  Physics**       \`physics.frames                         \`scipy\`,          risk, cli
                                                           \`numpy\`           

  **6 ---         physics.sgp4_propagator\`,               Layers 1-5          data, uncertainty,
  Propagators**   \`j2_corrector\`, \`drag_corrector\`,                        risk, cli
                  \`factory                                                    

  **7 ---         uncertainty.stm\`,                       Layers 1-6          data, risk, cli
  Uncertainty**   \`uncertainty.covariance_propagator\`,                       
                  \`uncertainty.monte_carlo                                    

  **8 --- Risk**  risk.bplane\`, \`risk.foster\`,          Layers 1-7          data, cli
                  \`risk.calculator\`, \`risk.alert                            

  **9 ---         conjunction.spatial_index\`,             Layers 1-8          cli
  Conjunction**   \`tca_finder\`, \`assessor                                   

  **10 --- CLI**  cli.main\`, \`cmd\_\*.py\`,              All layers +        ---
                  \`formatters\`, \`progress               \`click\`, \`rich\` 
  -------------------------------------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§6 Full Class Contracts**                                           |
|                                                                       |
| *Every class: constructor args, methods, return types, and behaviour  |
| spec*                                                                 |
+-----------------------------------------------------------------------+

**6.1 Physics Layer**

**6.1.1 BasePropagator «interface»**

  -----------------------------------------------------------------------
  📄 **physics/base.py**

  from abc import ABC, abstractmethod

  from datetime import datetime

  from oure.core.models import StateVector

  class BasePropagator(ABC):

  \"\"\"Abstract base for all orbit propagators.

  All concrete propagators must implement propagate() and propagate_to().

  The interface guarantees that any propagator can be substituted for

  any other without changes to consumers (Liskov Substitution).

  \"\"\"

  \@abstractmethod

  def propagate(

  self,

  state: StateVector,

  dt_seconds: float,

  ) -\> StateVector:

  \"\"\"Advance state by dt_seconds from state.epoch.

  Args:

  state: Initial state at t0.

  dt_seconds: Propagation interval in seconds. May be negative.

  Returns:

  New StateVector at t0 + dt_seconds.

  Raises:

  PropagationError: If propagation diverges or inputs are invalid.

  \"\"\"

  \@abstractmethod

  def propagate_to(

  self,

  state: StateVector,

  target_epoch: datetime,

  ) -\> StateVector:

  \"\"\"Propagate to an absolute UTC epoch.

  Args:

  state: Initial state at state.epoch.

  target_epoch: Desired output epoch (UTC).

  Returns:

  New StateVector at target_epoch.

  Raises:

  PropagationError: If propagation diverges.

  \"\"\"

  def propagate_sequence(

  self,

  state: StateVector,

  epochs: list\[datetime\],

  ) -\> list\[StateVector\]:

  \"\"\"Propagate to a list of epochs. Default: calls propagate_to() in
  loop.

  Override for batch-optimised implementations.

  \"\"\"

  return \[self.propagate_to(state, t) for t in epochs\]

  -----------------------------------------------------------------------

**6.1.2 SGP4Propagator**

  -----------------------------------------------------------------------
  📄 **physics/sgp4_propagator.py --- contract**

  class SGP4Propagator(BasePropagator):

  \"\"\"SGP4/SDP4 orbit propagator wrapping Vallado sgp4 library.

  Implements the full NORAD SGP4 model as defined in Hoots & Roehrich

  \(1980\) and updated by Vallado et al. (2006). Handles both LEO (SGP4)

  and deep space (SDP4) orbits via the sgp4 library auto-detection.

  Attributes:

  tle: Source TLERecord used to initialise the satellite.

  \_satrec: Underlying sgp4 Satrec object.

  \"\"\"

  def \_\_init\_\_(self, tle: TLERecord) -\> None:

  \# Initialise sgp4.api.Satrec.twoline2rv(tle.line1, tle.line2)

  \# Store as self.\_satrec

  \@classmethod

  def from_tle(cls, tle: TLERecord) -\> SGP4Propagator:

  \# Factory --- preferred construction path

  def propagate(self, state: StateVector, dt_seconds: float) -\>
  StateVector:

  \# Compute tsince_minutes = dt_seconds / 60

  \# Call self.\_satrec.sgp4(jd, fr) using epoch JD + dt

  \# Convert sgp4 output (km, km/s) directly to StateVector

  \# Raise PropagationError if sgp4 returns error code != 0

  def propagate_to(self, state: StateVector, target_epoch: datetime) -\>
  StateVector:

  \# Compute dt = (target_epoch - tle.epoch).total_seconds()

  \# Delegate to propagate(state, dt)

  def \_check_sgp4_error(self, error_code: int, sat_id: str) -\> None:

  \# Raise PropagationError with descriptive message for codes 1-6

  \# Code 0 = success, 1 = mean elements, 2 = mean motion,

  \# 3 = pert elements, 4 = semi-latus rectum, 5 = epoch elements,

  \# 6 = decayed satellite

  -----------------------------------------------------------------------

**6.1.3 J2PerturbationCorrector (Decorator)**

  -----------------------------------------------------------------------
  📄 **physics/j2_corrector.py --- contract**

  class J2PerturbationCorrector(BasePropagator):

  \"\"\"Adds first-order J2 perturbation on top of a base propagator.

  Implements the Decorator pattern. The J2 gravitational acceleration

  in ECI is computed analytically and added as a velocity/position

  increment after the base propagation.

  J2 acceleration (ECI Cartesian):

  coeff = -3/2 \* J2 \* MU \* R_E\^2 / \|r\|\^5

  a_x = coeff \* x \* (1 - 5\*(z/r)\^2)

  a_y = coeff \* y \* (1 - 5\*(z/r)\^2)

  a_z = coeff \* z \* (3 - 5\*(z/r)\^2)

  \"\"\"

  def \_\_init\_\_(self, base: BasePropagator) -\> None:

  self.\_base = base

  def propagate(self, state: StateVector, dt_seconds: float) -\>
  StateVector:

  \# 1. base_state = self.\_base.propagate(state, dt_seconds)

  \# 2. a_j2 = self.\_j2_acceleration(base_state.r)

  \# 3. Apply 1st-order integration:

  \# new_v = base_state.v + a_j2 \* dt_seconds

  \# new_r = base_state.r + 0.5 \* a_j2 \* dt_seconds\^2

  \# 4. Return new StateVector

  def \_j2_acceleration(self, r: np.ndarray) -\> np.ndarray:

  \# Compute the 3-component J2 acceleration vector

  \# See math in §7.1

  def \_gravity_gradient_j2(self, r: np.ndarray) -\> np.ndarray:

  \# Returns 3x3 ΔG_J2 tensor for STM Jacobian

  \# Used by uncertainty.stm.STMCalculator at fidelity=1

  -----------------------------------------------------------------------

**6.1.4 AtmosphericDragCorrector (Decorator)**

  -----------------------------------------------------------------------
  📄 **physics/drag_corrector.py --- contract**

  class AtmosphericDragCorrector(BasePropagator):

  \"\"\"Adds atmospheric drag deceleration on top of a base propagator.

  Drag model: Exponential atmosphere with Jacchia-Roberts solar

  flux correction. Density table covers 200-700 km altitude.

  Constructor Args:

  base (BasePropagator): Wrapped propagator.

  cd (float): Drag coefficient. Default 2.2.

  area_m2 (float): Cross-sectional area in m². Default 10.0.

  mass_kg (float): Satellite mass in kg. Default 500.0.

  solar_flux (float): F10.7 in SFU. Default 150.0.

  \"\"\"

  DENSITY_TABLE: list\[tuple\[float,float,float\]\] = \[

  \# (alt_km, rho_ref_kg_m3, scale_height_km)

  (200, 2.789e-10, 6.3),

  (300, 1.916e-11, 7.3),

  (400, 2.803e-12, 7.9),

  (500, 5.215e-13, 8.7),

  (600, 1.137e-13, 9.3),

  (700, 3.070e-14, 9.9),

  \]

  def atmospheric_density(self, altitude_km: float) -\> float:

  \# Look up bounding altitude band

  \# Exponential interpolation: rho = rho0 \* exp(-(h-h0)/H)

  \# Solar correction: rho \*= exp(JACCHIA_SOLAR_COUPLING \* (f10_7 -
  150))

  \# Return density in kg/m³

  def set_solar_flux(self, f10_7: float) -\> None:

  \# Hot-reload solar flux. Thread-safe.

  def drag_acceleration(self, r: np.ndarray, v: np.ndarray) -\>
  np.ndarray:

  \# v_rel = v - omega_earth x r (co-rotation subtraction)

  \# rho = atmospheric_density(\|r\| - R_EARTH_KM)

  \# a = -0.5 \* cd \* (area_m2/mass_kg) \* rho_kg_m3 \* \|v_rel_m_s\|\^2
  \* v_hat

  \# Return in km/s²

  -----------------------------------------------------------------------

**6.1.5 PropagatorFactory**

  -----------------------------------------------------------------------
  📄 **physics/factory.py --- contract**

  class PropagatorFactory:

  \"\"\"Assembles the layered propagator chain from config.

  Returns: AtmosphericDragCorrector(

  J2PerturbationCorrector(

  SGP4Propagator(tle)))

  The caller never needs to know the internal layer order.

  \"\"\"

  \@staticmethod

  def build(

  tle: TLERecord,

  solar_flux: float = SOLAR_FLUX_MEAN_SFU,

  include_j2: bool = True,

  include_drag: bool = True,

  cd: float = 2.2,

  area_m2: float = 10.0,

  mass_kg: float = 500.0,

  ) -\> BasePropagator:

  \# Builds and returns the configured propagator chain.

  \# Logs which layers are enabled at DEBUG level.

  \@staticmethod

  def build_from_config(

  tle: TLERecord,

  config: PipelineConfig,

  ) -\> BasePropagator:

  \# Convenience: reads cd, area_m2, mass_kg from config object

  -----------------------------------------------------------------------

**6.2 Uncertainty Layer**

**6.2.1 STMCalculator**

  -----------------------------------------------------------------------
  📄 **uncertainty/stm.py --- contract**

  class STMFidelity(IntEnum):

  TWO_BODY = 0 \# \~5µs --- matrix exponential, no perturbations

  J2_LINEAR = 1 \# \~50µs --- J2 corrected Jacobian

  NUMERICAL = 2 \# \~5ms --- finite-difference, 12 propagations

  class STMCalculator:

  \"\"\"Computes the 6×6 State Transition Matrix Φ(t, t0).

  The STM satisfies dΦ/dt = A(t)·Φ, Φ(t0,t0) = I6

  where A = ∂f/∂x is the equations-of-motion Jacobian.

  Evaluated via: Φ = expm(A·Δt) \[scipy.linalg.expm\]

  \"\"\"

  def \_\_init\_\_(

  self,

  fidelity: STMFidelity = STMFidelity.J2_LINEAR,

  propagator: BasePropagator \| None = None, \# Required for NUMERICAL

  ) -\> None:

  def compute(

  self,

  state: StateVector,

  dt_seconds: float,

  ) -\> np.ndarray: \# shape (6, 6)

  \# Dispatches to \_two_body_stm, \_j2_stm, or \_numerical_stm

  def \_build_jacobian_two_body(self, state: StateVector) -\> np.ndarray:

  \# A = \[\[0, I\], \[G_2body, 0\]\]

  \# G_2body_ij = mu/r\^3 \* (3\*ri\*rj/r\^2 - delta_ij)

  def \_build_jacobian_j2(self, state: StateVector) -\> np.ndarray:

  \# A = \[\[0, I\], \[G_2body + delta_G_J2, 0\]\]

  \# delta_G_J2 from J2PerturbationCorrector.\_gravity_gradient_j2()

  def \_numerical_stm(

  self, state: StateVector, dt: float, eps: float = 1.0

  ) -\> np.ndarray:

  \# Central difference: Phi\[:,i\] = (f(x+eps\*ei,dt) -
  f(x-eps\*ei,dt))/(2\*eps)

  \# eps: position perturbation in km; velocity eps = eps/1000 km/s

  \# Requires propagator to be set

  -----------------------------------------------------------------------

**6.2.2 CovariancePropagator**

  -----------------------------------------------------------------------
  📄 **uncertainty/covariance_propagator.py --- contract**

  class CovariancePropagator:

  \"\"\"Analytical covariance propagation via STM.

  Core equation: P(t) = Φ P0 Φᵀ + Q

  where Q (process noise) is a diagonal matrix accounting for

  unmodelled forces (SRP, outgassing, manoeuvres):

  Q = diag(q\*dt\^3/3 \[x3\], q\*dt \[x3\])

  with q = DEFAULT_Q_SCALE (km²/s³).

  \"\"\"

  DEFAULT_Q_SCALE: float = 1e-10 \# km²/s³

  def \_\_init\_\_(

  self,

  stm_calculator: STMCalculator \| None = None,

  q_scale: float = DEFAULT_Q_SCALE,

  ) -\> None:

  def propagate(

  self,

  covariance: CovarianceMatrix,

  reference_state: StateVector,

  dt_seconds: float,

  ) -\> CovarianceMatrix:

  \# 1. Phi = stm.compute(reference_state, dt_seconds)

  \# 2. P_prop = Phi @ P0 @ Phi.T

  \# 3. Q = self.\_process_noise(dt_seconds)

  \# 4. P_final = 0.5\*(P_prop + Q + (P_prop+Q).T) \[symmetrize\]

  \# 5. Validate P_final is positive semi-definite

  \# 6. Return new CovarianceMatrix at t0+dt

  def propagate_to(

  self,

  covariance: CovarianceMatrix,

  reference_state: StateVector,

  target_epoch: datetime,

  ) -\> CovarianceMatrix:

  def \_process_noise(self, dt: float) -\> np.ndarray:

  \# Returns 6x6 Q matrix

  def \_ensure_positive_semidefinite(

  self, P: np.ndarray, eps: float = 1e-12

  ) -\> np.ndarray:

  \# If Cholesky fails: P = P + eps\*I, retry up to 5 times

  \# If still fails: raise CovarianceNotPositiveDefiniteError

  -----------------------------------------------------------------------

**6.2.3 MonteCarloUncertaintyPropagator**

  -----------------------------------------------------------------------
  📄 **uncertainty/monte_carlo.py --- contract**

  \@dataclass

  class MonteCarloResult:

  nominal_state: StateVector

  ghost_states: list\[StateVector\] \# All N propagated samples

  sample_covariance: np.ndarray \# 6x6 from ensemble

  sample_mean: np.ndarray \# 6-vector

  n_samples: int

  outlier_fraction: float \# Fraction \>3σ Mahalanobis

  wallclock_seconds: float

  class MonteCarloUncertaintyPropagator:

  \"\"\"Monte Carlo ghost trajectory propagation.

  Sampling: x_i = x0 + L·ξ_i where L = chol(P0), ξ_i \~ N(0,I6)

  Reconstruction: P_mc = 1/(N-1) \* Σ (xi - x_mean)(xi - x_mean)ᵀ

  \"\"\"

  def \_\_init\_\_(

  self,

  propagator: BasePropagator,

  n_samples: int = 1000,

  random_seed: int \| None = 42,

  n_workers: int = 1, \# \>1 enables multiprocessing

  ) -\> None:

  def run(

  self,

  initial_state: StateVector,

  initial_covariance: CovarianceMatrix,

  target_epoch: datetime,

  ) -\> MonteCarloResult:

  \# 1. Cholesky decompose P0 (with regularisation fallback)

  \# 2. Draw N samples via L @ rng.standard_normal((6,N))

  \# 3. Build ghost StateVectors

  \# 4. Propagate: serial if n_workers=1, concurrent.futures if \>1

  \# 5. Stack results, compute sample mean and covariance

  \# 6. Compute Mahalanobis distances; flag outlier_fraction

  \# 7. Record wallclock time

  def cross_validate(

  self,

  mc_result: MonteCarloResult,

  analytical_cov: CovarianceMatrix,

  tolerance: float = 0.30,

  ) -\> dict\[str, float \| bool \| str\]:

  \# Frobenius relative difference between P_mc and P_analytical

  \# Returns: {relative_diff, linear_valid, recommendation}

  -----------------------------------------------------------------------

**6.3 Conjunction & Risk Layer**

**6.3.1 KDTreeSpatialIndex**

  -----------------------------------------------------------------------
  📄 **conjunction/spatial_index.py --- contract**

  class KDTreeSpatialIndex:

  \"\"\"KD-Tree wrapper for fast satellite proximity queries.

  Reduces O(N²) pairwise screening to O(N log N) per timestep.

  Usage:

  index = KDTreeSpatialIndex(positions) \# shape (N, 3)

  neighbours = index.query_radius(point, radius_km)

  \"\"\"

  def \_\_init\_\_(self, positions: np.ndarray) -\> None:

  \# positions: shape (N, 3), ECI km

  \# Build scipy.spatial.KDTree

  def query_radius(

  self,

  point: np.ndarray, \# shape (3,) ECI km

  radius_km: float,

  ) -\> list\[int\]: \# indices into original positions array

  def query_k_nearest(

  self,

  point: np.ndarray,

  k: int,

  ) -\> tuple\[list\[float\], list\[int\]\]: \# (distances, indices)

  \@property

  def size(self) -\> int: \# Number of indexed points

  -----------------------------------------------------------------------

**6.3.2 TCARefinementEngine**

  -----------------------------------------------------------------------
  📄 **conjunction/tca_finder.py --- contract**

  class TCARefinementEngine:

  \"\"\"Golden-section search for Time of Closest Approach.

  Minimises ρ(t) = \|r_p(t) - r_s(t)\| over a time window.

  Golden ratio: φ = (√5 - 1)/2 ≈ 0.6180

  Convergence: \|b-a\| \< tolerance in ceil(log(Δt/tol)/log(1/φ)) steps

  At Δt=30min, tol=0.1s: converges in \~60 iterations.

  \"\"\"

  GOLDEN_RATIO: float = 0.6180339887498949

  def \_\_init\_\_(

  self,

  tolerance_seconds: float = 0.1,

  max_iterations: int = 100,

  ) -\> None:

  def find_tca(

  self,

  primary_state: StateVector,

  primary_propagator: BasePropagator,

  secondary_state: StateVector,

  secondary_propagator: BasePropagator,

  search_start: datetime,

  search_end: datetime,

  ) -\> tuple\[datetime, float\]: \# (tca_epoch, miss_distance_km)

  def \_range_at(

  self, dt_offset: float, \...

  ) -\> float:

  \# Returns \|r_p(t0+dt) - r_s(t0+dt)\| in km

  \# Called O(120) times per TCA refinement --- must be fast

  -----------------------------------------------------------------------

**6.3.3 BPlaneProjector**

  -----------------------------------------------------------------------
  📄 **risk/bplane.py --- contract**

  class BPlaneProjector:

  \"\"\"Constructs the B-plane reference frame and projects covariances.

  The B-plane is perpendicular to v_rel at TCA.

  Basis vectors (right-handed):

  η̂ = v̂\_rel (along relative velocity --- integrated out)

  ξ̂ = (ŷ × v̂\_rel)/\|ŷ × v̂\_rel\| (in-plane, \~radial)

  ζ̂ = v̂\_rel × ξ̂ (in-plane, \~along-track)

  If ŷ is nearly parallel to v̂\_rel, falls back to ẑ as reference.

  Raises BPlaneError if v_rel is degenerate (\|v_rel\| \< 1e-9 km/s).

  \"\"\"

  def project(

  self,

  conjunction: ConjunctionEvent,

  ) -\> BPlaneProjection:

  \# 1. v_rel = v_p - v_s; v_hat = v_rel / \|v_rel\|

  \# 2. Choose ref = \[0,1,0\] unless \|dot(v_hat,ref)\| \> 0.9 → use
  \[0,0,1\]

  \# 3. xi_hat = cross(ref, v_hat) / \|\...\|

  \# 4. zeta_hat = cross(v_hat, xi_hat) / \|\...\|

  \# 5. T = stack(\[xi_hat, zeta_hat\]) shape (2,3)

  \# 6. C_3d = C_primary\[:3,:3\] + C_secondary\[:3,:3\]

  \# 7. C_2d = T @ C_3d @ T.T shape (2,2)

  \# 8. b_3d = r_p - r_s at TCA

  \# 9. b_2d = T @ b_3d shape (2,)

  \# 10. Return BPlaneProjection

  def plot_bplane(

  self,

  projection: BPlaneProjection,

  hard_body_radius_km: float,

  output_path: Path \| None = None,

  ) -\> None: \# \[OPTIONAL\] matplotlib visualisation

  -----------------------------------------------------------------------

**6.3.4 FosterPcCalculator**

  -----------------------------------------------------------------------
  📄 **risk/foster.py --- contract**

  class PcMethod(str, Enum):

  NUMERICAL = \'numerical\' \# scipy dblquad --- default

  FOSTER_SERIES = \'series\' \# Foster (1992) analytic series

  MONTE_CARLO = \'mc\' \# From MC ghost intersection count

  class FosterPcCalculator:

  \"\"\"Probability of Collision via Foster\'s 2D B-plane integral.

  Pc = ∬\_{D} f(ξ-b_ξ, ζ-b_ζ; C_2d) dξ dζ

  D = {(ξ,ζ): ξ²+ζ² ≤ R²} (collision disk)

  f = bivariate normal PDF with covariance C_2d

  The hard-body radius R = r_primary + r_secondary \[km\].

  \"\"\"

  def \_\_init\_\_(

  self,

  hard_body_radius_km: float,

  method: PcMethod = PcMethod.NUMERICAL,

  integration_sigma: float = 5.0, \# Box half-width in sigma

  series_terms: int = 200,

  ) -\> None:

  def compute(

  self,

  b_miss: np.ndarray, \# shape (2,) miss vector in B-plane (km)

  C_2d: np.ndarray, \# shape (2,2) combined covariance (km²)

  ) -\> float: \# Pc ∈ \[0, 1\]

  def \_numerical_integration(

  self, b: np.ndarray, C: np.ndarray

  ) -\> float:

  \# dblquad over ±integration_sigma\*σ box

  \# Integrand = Gaussian PDF \* inside_disk indicator

  \# epsabs=1e-12, epsrel=1e-8

  def \_foster_series(

  self, b: np.ndarray, C: np.ndarray

  ) -\> float:

  \# Eigendecompose C → (λ1, λ2)

  \# u = bᵀ C⁻¹ b / 2 (normalised miss distance)

  \# v = R² / (2\*sqrt(λ1\*λ2)) (normalised disk radius)

  \# Σ\_{n=0}\^{N} exp(-u) \* u\^n/n! \* gammainc(n+1, v)

  def \_mc_pc(

  self,

  ghost_b_vecs: np.ndarray, \# shape (N,2) MC miss vectors in B-plane

  ) -\> float:

  \# Count fraction of ghosts with \|b_i\| \<= R

  \# Returns count/N

  -----------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§7 Physics & Math Reference**                                       |
|                                                                       |
| *Equations the agent must implement --- with derivations*             |
+-----------------------------------------------------------------------+

**7.1 J2 Gravity Gradient Tensor**

The J2 perturbation potential is: U_J2 = −μ J2 R_E² / (2r³) · (3sin²φ −
1)

Taking the gradient to get acceleration and then differentiating again
for the Jacobian gives the 3×3 correction tensor ΔG_J2 with components:

  -----------------------------------------------------------------------
  📄 **J2 gravity gradient tensor elements**

  coeff = -3/2 \* J2 \* MU \* R_E\^2 / \|r\|\^5

  z_r = r\[2\] / \|r\| \# sin(geocentric latitude)

  a_J2 = coeff \* \[

  r\[0\] \* (1 - 5\*z_r\^2),

  r\[1\] \* (1 - 5\*z_r\^2),

  r\[2\] \* (3 - 5\*z_r\^2),

  \]

  \# Jacobian: delta_G\[i,j\] = d(a_J2\[i\])/d(r\[j\])

  \# For i != 2, j != 2:

  \# delta_G\[i,j\] = coeff/\|r\| \* (1-5\*z_r\^2) \* (delta_ij -
  r\[i\]\*r\[j\]/\|r\|\^2)

  \# - coeff/\|r\| \* 10\*z_r\*r\[i\]\*e_z\[j\]/\|r\|

  \# + coeff/\|r\| \* 35\*z_r\^2\*r\[i\]\*r\[j\]/\|r\|\^2

  -----------------------------------------------------------------------

**7.2 Atmosphere Density Interpolation**

  -----------------------------------------------------------------------
  📄 **atmospheric_density algorithm**

  def atmospheric_density(alt_km: float, f10_7: float) -\> float:

  \# 1. Clamp altitude: alt = max(200, min(700, alt_km))

  \# 2. Find i where DENSITY_TABLE\[i\]\[0\] \<= alt \<
  DENSITY_TABLE\[i+1\]\[0\]

  \# 3. h0, rho0, H = DENSITY_TABLE\[i\]

  \# 4. rho_base = rho0 \* exp(-(alt - h0) / H)

  \# 5. solar_correction = exp(JACCHIA_SOLAR_COUPLING \* (f10_7 - 150.0))

  \# 6. return rho_base \* solar_correction \[kg/m³\]

  \#

  \# Above 700km: return 1e-14 (near-vacuum)

  \# Below 200km: not supported --- raise ValueError

  -----------------------------------------------------------------------

**7.3 Kepler Equation --- Newton-Raphson Solver**

  -----------------------------------------------------------------------
  📄 **kepler.py --- algorithm**

  def solve_kepler_newton(

  M: float, \# Mean anomaly (radians)

  e: float, \# Eccentricity

  tol: float = 1e-12,

  max_iter: int = 50,

  ) -\> float:

  \# Returns Eccentric Anomaly E (radians)

  \#

  \# Kepler\'s equation: M = E - e\*sin(E)

  \# Newton-Raphson: E\_{k+1} = E_k - f(E_k)/f\'(E_k)

  \# where f(E) = E - e\*sin(E) - M

  \# f\'(E) = 1 - e\*cos(E)

  \#

  \# Initial guess: E0 = M (good for e \< 0.1)

  \# For e \> 0.8 use: E0 = pi

  \#

  \# Convergence check: \|dE\| \< tol

  \# If not converged in max_iter: raise KeplerConvergenceError

  \#

  \# Typical LEO (e\~0.001): converges in 2-3 iterations

  \# High eccentricity (e\~0.7): converges in 5-8 iterations

  -----------------------------------------------------------------------

**7.4 Covariance Propagation --- Step-by-Step**

  ------------------------------------------------------------------------------
  **Step**   **Operation**                  **Notes**
  ---------- ------------------------------ ------------------------------------
  **1**      Compute STM: Φ = expm(A · Δt)  A is 6×6 Jacobian at reference state

  **2**      Propagate: P_prop = Φ P₀ Φᵀ    Exact for linear dynamics

  **3**      Process noise: Q =             q ≈ 1×10⁻¹⁰ km²/s³
             diag(q·Δt³/3 \[×3\], q·Δt      
             \[×3\])                        

  **4**      Add noise: P_raw = P_prop + Q  Models unmodelled forces

  **5**      Symmetrize: P = ½(P_raw +      Guards floating-point drift
             P_rawᵀ)                        

  **6**      Validate PD: cholesky(P) → if  Regularization fallback
             fail, P += εI                  
  ------------------------------------------------------------------------------

**7.5 Foster\'s Algorithm --- Numerical Integration**

  -----------------------------------------------------------------------
  📄 **foster.py --- numerical_integration**

  def \_numerical_integration(b, C, R, sigma_mult=5.0) -\> float:

  C_inv = np.linalg.inv(C)

  det_C = np.linalg.det(C)

  norm_factor = 1.0 / (2\*pi \* sqrt(abs(det_C)))

  R_sq = R\*\*2

  def integrand(zeta: float, xi: float) -\> float:

  if xi\*\*2 + zeta\*\*2 \> R_sq:

  return 0.0 \# Outside collision disk

  u = np.array(\[xi - b\[0\], zeta - b\[1\]\])

  return norm_factor \* exp(-0.5 \* u @ C_inv @ u)

  sigma_x = sqrt(C\[0,0\])

  sigma_z = sqrt(C\[1,1\])

  xi_lo = -sigma_mult \* sigma_x

  xi_hi = sigma_mult \* sigma_x

  result, error = dblquad(

  integrand,

  xi_lo, xi_hi,

  lambda xi: -sigma_mult \* sigma_z,

  lambda xi: sigma_mult \* sigma_z,

  epsabs=1e-12, epsrel=1e-8,

  )

  return float(np.clip(result, 0.0, 1.0))

  -----------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§8 Data Layer Specification**                                       |
|                                                                       |
| *API contracts, caching strategy, and retry logic*                    |
+-----------------------------------------------------------------------+

**8.1 CacheManager**

  -----------------------------------------------------------------------
  📄 **data/cache.py --- schema and contract**

  \# SQLite schema --- agent must create on first init

  CREATE_TLE_TABLE = \'\'\'

  CREATE TABLE IF NOT EXISTS tle_records (

  sat_id TEXT PRIMARY KEY,

  name TEXT NOT NULL,

  line1 TEXT NOT NULL,

  line2 TEXT NOT NULL,

  tle_epoch TEXT NOT NULL,

  fetched_at TEXT NOT NULL,

  inclination_deg REAL,

  raan_deg REAL,

  eccentricity REAL,

  arg_perigee_deg REAL,

  mean_anomaly_deg REAL,

  mean_motion REAL,

  bstar REAL

  )\'\'\'

  CREATE_KV_TABLE = \'\'\'

  CREATE TABLE IF NOT EXISTS kv_cache (

  key TEXT PRIMARY KEY,

  value_json TEXT NOT NULL,

  fetched_at REAL NOT NULL,

  ttl_seconds REAL NOT NULL

  )\'\'\'

  \# CacheManager must implement:

  def get(key: str) -\> str \| None:

  \# Return None if expired or missing

  def set(key: str, value: str, ttl_seconds: float = 3600.0) -\> None:

  def get_tle(sat_id: str, max_age_hours: float = 6.0) -\> TLERecord \|
  None:

  def put_tle(record: TLERecord) -\> None:

  def put_many_tles(records: list\[TLERecord\]) -\> None:

  \# Use executemany() --- single transaction for batch writes

  def stats(self) -\> dict\[str,int\|float\]:

  \# Returns: {n_tles, n_kv_entries, db_size_kb, oldest_tle_age_h}

  def purge_expired(self) -\> int:

  \# Delete expired kv_cache entries. Returns count deleted.

  def clear_tles(self) -\> int:

  \# Truncate tle_records. Returns count deleted.

  -----------------------------------------------------------------------

**8.2 SpaceTrackFetcher --- API Details**

  --------------------------------------------------------------------------------------------------------------------------
  **Endpoint**                                                                 **Method**   **Purpose**
  ---------------------------------------------------------------------------- ------------ --------------------------------
  **https://www.space-track.org/ajaxauth/login**                               POST         Authenticate --- body:
                                                                                            {identity, password}

  **https://www.space-track.org/basicspacedata/query/class/tle_latest/\...**   GET          Fetch TLEs --- returns JSON
                                                                                            array

  **https://www.space-track.org/ajaxauth/logout**                              GET          Logout --- always call in
                                                                                            finally block
  --------------------------------------------------------------------------------------------------------------------------

  -----------------------------------------------------------------------
  📄 **SpaceTrackFetcher --- retry and auth contract**

  class SpaceTrackFetcher(BaseDataFetcher):

  \# Auth: POST login, save session cookie, GET data, GET logout

  \# Always logout in a finally block --- quota is per-session

  \#

  \# Retry strategy (use tenacity):

  \# \@retry(stop=stop_after_attempt(3),

  \# wait=wait_exponential(multiplier=1, min=2, max=30),

  \# retry=retry_if_exception_type(requests.Timeout))

  \#

  \# Rate limit awareness:

  \# If response contains \'Request Limit Exceeded\': sleep 60s, retry
  once

  \# Log warning with current time and retry time

  \#

  \# URL construction for multi-ID queries:

  \# IDs are comma-joined: /NORAD_CAT_ID/25544,43205,40379/

  \# Batch max: 200 IDs per request

  \# For \>200 IDs: chunk into batches of 200, merge results

  def fetch(

  self,

  sat_ids: list\[str\] \| None = None,

  epoch_range_days: float = 30.0,

  ) -\> list\[TLERecord\]:

  \# Check cache for each ID. Separate into hit/miss lists.

  \# Fetch miss list from network in batches of 200.

  \# Cache all returned records.

  \# Merge and return.

  -----------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§9 CLI Specification**                                              |
|                                                                       |
| *All commands, options, output format, and exit codes*                |
+-----------------------------------------------------------------------+

**9.1 Command Hierarchy**

  -----------------------------------------------------------------------
  📄 **CLI tree**

  oure \[\--verbose\] \[\--log-file PATH\] \[\--db PATH\]

  │

  ├── fetch Fetch TLE and solar flux data

  │ \--sat-id TEXT \[multiple\] NORAD IDs to fetch

  │ \--all-leo Fetch all LEO catalog objects

  │ \--output PATH Save JSON output

  │ \--force-refresh Bypass cache

  │ \--format \[table\|json\|csv\] Output format (default: table)

  │

  ├── analyze Run full conjunction assessment pipeline

  │ \--primary TEXT \[required\] Primary NORAD ID

  │ \--secondary TEXT \[multiple\] Secondary NORAD IDs

  │ \--secondaries-file PATH JSON file of secondary IDs

  │ \--look-ahead FLOAT Hours to look ahead (default: 72)

  │ \--screening-dist FLOAT KD-Tree radius km (default: 5.0)

  │ \--mc-samples INT Monte Carlo N (default: 1000)

  │ \--hbr FLOAT Hard-body radius metres (default: 20.0)

  │ \--fidelity \[0\|1\|2\] STM fidelity (default: 1)

  │ \--output PATH Save results JSON

  │ \--no-mc Skip Monte Carlo cross-validation

  │

  ├── monitor Continuous re-evaluation loop

  │ \--primary TEXT \[required\]

  │ \--secondaries-file PATH \[required\]

  │ \--alert-threshold FLOAT Pc for RED alert (default: 1e-3)

  │ \--interval INT Seconds between runs (default: 3600)

  │ \--max-runs INT Stop after N runs

  │ \--webhook-url TEXT POST RED alerts here

  │

  ├── cache Manage local cache

  │ \--status Print statistics

  │ \--clear Clear all data

  │ \--clear-tles Clear only TLE records

  │ \--purge-expired Remove stale KV entries

  │

  └── report Generate risk assessment report

  \--results-file PATH \[required\] JSON from \`analyze\`

  \--format \[txt\|json\|csv\] (default: txt)

  \--output PATH

  -----------------------------------------------------------------------

**9.2 Exit Codes**

  --------------------------------------------------------------------------
  **Code**   **Meaning**         **When**
  ---------- ------------------- -------------------------------------------
  **0**      Success             Normal completion, no alerts triggered

  **1**      General error       Unhandled exception, bad arguments

  **2**      Auth failure        Space-Track login rejected

  **3**      Network error       API unreachable after all retries

  **10**     YELLOW alert        \`analyze\` found Pc \>= yellow threshold

  **11**     RED alert           \`analyze\` found Pc \>= red threshold
  --------------------------------------------------------------------------

**9.3 Console Output Format**

+---+-------------------------------------------------------------------+
| * | **Agent Task**                                                    |
| * |                                                                   |
| 📋 | Use the \`rich\` library for ALL console output. Use Rich Panel, |
| * | Table, Progress, and Console objects. Never use bare print() in   |
| * | CLI code.                                                         |
+---+-------------------------------------------------------------------+

  -----------------------------------------------------------------------------
  📄 **Expected analyze output (Rich-formatted)**

  ╭─────────────────────────────────────────────────────╮

  │ OURE Conjunction Assessment │

  │ Primary: ISS (25544) │ Look-ahead: 72h │

  ╰─────────────────────────────────────────────────────╯

  Fetching data ━━━━━━━━━━━━━━━━━━━━━━ 100% 3/3

  KD-Tree screening ━━━━━━━━━━━━━━━━━━ 100% 27,143 objects

  TCA refinement ━━━━━━━━━━━━━━━━━━━━━ 100% 4 candidates

  Pc calculation ━━━━━━━━━━━━━━━━━━━━━ 100% 4 events

  ┌──────┬────────────┬───────────────┬─────────────┬──────────────┬────────┐

  │ \# │ Sec ID │ TCA (UTC) │ Miss (km) │ Pc │ Level │

  ├──────┼────────────┼───────────────┼─────────────┼──────────────┼────────┤

  │ 1 │ 43205 │ 2024-01-16 │ 0.183 │ 2.14e-04 │ 🟡 │

  │ │ │ 14:23:11 │ │ │ YELLOW│

  ├──────┼────────────┼───────────────┼─────────────┼──────────────┼────────┤

  │ 2 │ 47813 │ 2024-01-17 │ 1.041 │ 8.32e-07 │ 🟢 │

  │ │ │ 09:17:44 │ │ │ GREEN │

  └──────┴────────────┴───────────────┴─────────────┴──────────────┴────────┘

  ⚠ YELLOW ALERT --- Max Pc = 2.14e-04 (threshold: 1.00e-05)

  Action: Increase tracking cadence. Prepare contingency manoeuvre.

  -----------------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§10 Test Suite Specification**                                      |
|                                                                       |
| *Exact test cases the agent must implement*                           |
+-----------------------------------------------------------------------+

**10.1 Unit Tests --- Physics**

  --------------------------------------------------------------------------------------
  **Test File**        **Test Function**                **What It Verifies**
  -------------------- -------------------------------- --------------------------------
  **test_kepler.py**   test_circular_orbit              e=0 → E=M (identity)

  **test_kepler.py**   test_small_eccentricity          e=0.001, M=45°, \|E-M\| \< 0.01°

  **test_kepler.py**   test_high_eccentricity           e=0.9, M=180°, converges

  **test_kepler.py**   test_convergence_failure         e=1.1 raises
                                                        KeplerConvergenceError

  **test_frames.py**   test_pqw_to_eci_circular         i=0, ω=0 → r is in x-y plane

  **test_frames.py**   test_pqw_to_eci_polar            i=90° → r stays in x-z plane

  **test_frames.py**   test_roundtrip_eci_to_elements   elements → ECI → elements,
                                                        \<1e-10 error

  **test_sgp4.py**     test_iss_propagation_24h         ISS TLE, 24h propagation,
                                                        altitude 390-420km

  **test_sgp4.py**     test_known_state_vector          Reference TLE with published ECI
                                                        state, \<1km error

  **test_j2.py**       test_raan_drift_rate             RAAN precession matches formula
                                                        dΩ/dt to 1%

  **test_drag.py**     test_density_at_400km            F10.7=150 → rho ≈ 2.8e-12 kg/m³

  **test_drag.py**     test_solar_flux_sensitivity      F10.7=250 vs 70 → \~10× density
                                                        ratio

  **test_drag.py**     test_drag_reduces_altitude       24h propagation lowers apogee
  --------------------------------------------------------------------------------------

**10.2 Unit Tests --- Uncertainty**

  ------------------------------------------------------------------------------------------------------
  **Test File**             **Test Function**                           **What It Verifies**
  ------------------------- ------------------------------------------- --------------------------------
  **test_stm.py**           test_stm_identity_at_zero                   dt=0 → Φ = I₆

  **test_stm.py**           test_stm_symmetry                           Φ(t,0)·Φ(0,t)=I₆ within 1e-6

  **test_stm.py**           test_j2_vs_twobody                          J2 STM deviates from 2-body for
                                                                        LEO

  **test_covariance.py**    test_covariance_grows_in_time               tr(P(t)) \> tr(P(0)) for t\>0

  **test_covariance.py**    test_positive_definite_always               P remains PD after propagation

  **test_covariance.py**    test_process_noise_symmetric                Q is symmetric

  **test_monte_carlo.py**   test_sample_mean_near_nominal               MC mean within 3σ of nominal for
                                                                        N=5000

  **test_monte_carlo.py**   test_sample_covariance_matches_analytical   Frobenius diff \< 30% for 1h
                                                                        propagation

  **test_monte_carlo.py**   test_outlier_fraction                       outlier_fraction \< 0.005 for
                                                                        valid Gaussian
  ------------------------------------------------------------------------------------------------------

**10.3 Unit Tests --- Risk Math**

  ------------------------------------------------------------------------------------------
  **Test File**        **Test Function**                    **What It Verifies**
  -------------------- ------------------------------------ --------------------------------
  **test_bplane.py**   test_bplane_perpendicular_to_vrel    ξ̂·v_rel = 0, ζ̂·v_rel = 0

  **test_bplane.py**   test_bplane_orthonormal              \|ξ̂\|=\|ζ̂\|=1, ξ̂·ζ̂=0

  **test_bplane.py**   test_projection_reduces_dimension    C_2d shape is (2,2)

  **test_foster.py**   test_pc_zero_for_large_miss          miss=100km, σ=1km → Pc \< 1e-100

  **test_foster.py**   test_pc_half_for_centred_gaussian    miss=0, isotropic σ, large R →
                                                            Pc→1

  **test_foster.py**   test_numerical_vs_series_agreement   Both methods agree to 5% for
                                                            typical input

  **test_foster.py**   test_pc_clipped_to_zero_one          Result always in \[0,1\]

  **test_foster.py**   test_known_reference_case            Chan (2008) Table 1 reference:
                                                            Pc=1.12e-5
  ------------------------------------------------------------------------------------------

**10.4 Integration Tests**

  --------------------------------------------------------------------------------------
  **Test File**               **Test Function**           **What It Verifies**
  --------------------------- --------------------------- ------------------------------
  **test_pipeline_full.py**   test_iss_vs_debris_24h      Full pipeline: TLE→Pc for a
                                                          synthetic conjunction

  **test_pipeline_full.py**   test_green_conjunction      Large miss distance → GREEN,
                                                          Pc \< 1e-10

  **test_pipeline_full.py**   test_red_conjunction        Injected close approach → RED,
                                                          Pc \> 1e-3

  **test_pipeline_full.py**   test_mc_cross_validation    MC and analytical agree within
                                                          30%

  **test_cli_analyze.py**     test_analyze_exits_green    Green case → exit code 0

  **test_cli_analyze.py**     test_analyze_exits_yellow   Yellow case → exit code 10

  **test_cli_analyze.py**     test_analyze_json_output    Output JSON has required keys
  --------------------------------------------------------------------------------------

**10.5 conftest.py --- Required Fixtures**

  -----------------------------------------------------------------------
  📄 **tests/conftest.py --- fixture list**

  \# The agent must implement ALL of the following pytest fixtures:

  \@pytest.fixture

  def iss_tle() -\> TLERecord:

  \# Return TLERecord for ISS (NORAD 25544) from
  fixtures/sample_tles.json

  \@pytest.fixture

  def default_covariance() -\> CovarianceMatrix:

  \# 6x6 diagonal: σ_pos=1km, σ_vel=1m/s

  \@pytest.fixture

  def circular_state_400km() -\> StateVector:

  \# Circular orbit, 400km altitude, equatorial, t=J2000

  \@pytest.fixture

  def iss_propagator(iss_tle) -\> BasePropagator:

  \# PropagatorFactory.build(iss_tle, solar_flux=150.0)

  \@pytest.fixture

  def synthetic_conjunction() -\> ConjunctionEvent:

  \# Manually constructed close approach: miss=0.5km, v_rel=10km/s

  \# primary_id=\'25544\', secondary_id=\'99999\'

  \@pytest.fixture

  def cache_manager(tmp_path) -\> CacheManager:

  \# CacheManager(db_path=tmp_path / \'test_cache.db\')

  \@pytest.fixture

  def mock_spacetrack(monkeypatch, iss_tle):

  \# Monkeypatch SpaceTrackFetcher.\_fetch_from_network

  \# Returns \[iss_tle\] for any input without network call

  -----------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§11 Quality Gates**                                                 |
|                                                                       |
| *Automated checks the agent must pass before the project is complete* |
+-----------------------------------------------------------------------+

**11.1 Gate Checklist**

+---+-------------------------------------------------------------------+
| * | **All Gates Must Be Green**                                       |
| * |                                                                   |
| 🔒 | The agent must run each gate and fix all failures before         |
| * | declaring the project complete. Do not submit with failing gates. |
| * |                                                                   |
+---+-------------------------------------------------------------------+

  ---------------------------------------------------------------------------
  **Gate**        **Command**                **Pass Condition**
  --------------- -------------------------- --------------------------------
  **G1 --- Lint** ruff check oure/ tests/    Zero errors or warnings

  **G2 ---        ruff format \--check oure/ Zero reformatting needed
  Format**        tests/                     

  **G3 ---        mypy oure/ \--strict       Zero type errors
  Types**                                    

  **G4 --- Unit   pytest tests/unit/ -v      All tests pass
  Tests**                                    

  **G5 ---        pytest tests/integration/  All tests pass
  Integration**   -v                         

  **G6 ---        pytest \--cov=oure         Coverage \>= 80%
  Coverage**      \--cov-fail-under=80       

  **G7 --- Import ruff check \--select I     Isort clean
  order**         oure/                      

  **G8 ---        pip install bandit &&      No HIGH/CRITICAL issues
  Security**      bandit -r oure/            

  **G9 ---        pip install build &&       Wheel and sdist created
  Build**         python -m build            

  **G10 ---       pip install dist/\*.whl && \`oure\` command runs
  Install**       oure \--help               
  ---------------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§12 Logging & Observability**                                       |
|                                                                       |
| *Structured logging, log levels, and key events to instrument*        |
+-----------------------------------------------------------------------+

**12.1 Logging Setup**

  -----------------------------------------------------------------------
  📄 **core/logging_config.py --- contract**

  \"\"\"Structured logging configuration using structlog.\"\"\"

  import structlog

  import logging

  from enum import Enum

  class LogFormat(str, Enum):

  CONSOLE = \"console\" \# Human-readable (Rich renderer)

  JSON = \"json\" \# Machine-readable (for log aggregators)

  def configure_logging(

  level: str = \'INFO\',

  format: LogFormat = LogFormat.CONSOLE,

  log_file: str \| None = None,

  ) -\> None:

  \# Configure structlog processors:

  \# - structlog.stdlib.add_log_level

  \# - structlog.stdlib.add_logger_name

  \# - structlog.processors.TimeStamper(fmt=\'iso\')

  \# - structlog.processors.StackInfoRenderer()

  \# - structlog.processors.format_exc_info

  \# - JSONRenderer() or ConsoleRenderer() based on format

  def get_logger(name: str) -\> structlog.BoundLogger:

  return structlog.get_logger(name)

  -----------------------------------------------------------------------

**12.2 Mandatory Log Events**

  ---------------------------------------------------------------------------------------
  **Module**                 **Log     **Event / Message**      **Key Context Fields**
                             Level**                            
  -------------------------- --------- ------------------------ -------------------------
  **data.spacetrack**        INFO      Authenticated with       username (masked)
                                       Space-Track.org          

  **data.spacetrack**        INFO      Fetched N TLE records    n_records, duration_ms

  **data.spacetrack**        WARNING   Rate limit hit ---       sleep_seconds, retry_at
                                       sleeping Xs              

  **data.cache**             DEBUG     Cache HIT for sat_id=X   sat_id, age_hours

  **data.cache**             DEBUG     Cache MISS for sat_id=X  sat_id

  **physics.factory**        DEBUG     Propagator chain         layers_enabled
                                       assembled                

  **uncertainty.mc**         INFO      Monte Carlo run complete n_samples, outlier_frac,
                                                                wallclock_s

  **conjunction.assessor**   INFO      KD-Tree screening        n_objects, n_candidates,
                                       complete                 step_count

  **risk.calculator**        INFO      Pc computed              primary_id, secondary_id,
                                                                pc, method

  **risk.alert**             WARNING   YELLOW alert --- Pc=X    pc, threshold, tca, ids
                                       exceeds threshold Y      

  **risk.alert**             ERROR     RED alert --- Pc=X       pc, threshold, tca, ids
                                       exceeds threshold Y      
  ---------------------------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§13 Error Handling Strategy**                                       |
|                                                                       |
| *How every layer handles failures --- no silent swallows*             |
+-----------------------------------------------------------------------+

**13.1 Rules**

-   NEVER catch \`Exception\` broadly --- catch only specific expected
    exception types.

-   NEVER swallow exceptions silently --- always log.error() before
    re-raising or converting.

-   Physics exceptions (PropagationError, CovarianceError) must NOT
    propagate to the CLI --- the assessor catches them and marks the
    pair as \'computation_failed\'.

-   Network exceptions (DataFetchError) must use tenacity retry with
    exponential backoff, then propagate to CLI which shows a
    user-friendly message.

-   All public API functions that can fail must document the exception
    in their Raises: docstring section.

**13.2 Retry Configuration**

  -----------------------------------------------------------------------
  📄 **data/spacetrack.py --- retry decorator**

  from tenacity import (

  retry, stop_after_attempt, wait_exponential,

  retry_if_exception_type, before_sleep_log

  )

  import logging

  \_RETRY_POLICY = retry(

  stop=stop_after_attempt(3),

  wait=wait_exponential(multiplier=1, min=2, max=60),

  retry=retry_if_exception_type(

  (requests.Timeout, requests.ConnectionError)

  ),

  before_sleep=before_sleep_log(logging.getLogger(\'oure.data\'),
  logging.WARNING),

  reraise=True,

  )

  \# Apply to \_fetch_from_network():

  \@\_RETRY_POLICY

  def \_fetch_from_network(self, \...) -\> list\[TLERecord\]:

  \...

  -----------------------------------------------------------------------

+-----------------------------------------------------------------------+
| **§14 Professional Standards Checklist**                              |
|                                                                       |
| *Final review the agent must self-perform before declaring done*      |
+-----------------------------------------------------------------------+

**14.1 Code Quality**

-   Every module has a module-level docstring explaining purpose, key
    classes, and example usage.

-   Every class has a class-level docstring with Attributes: section
    listing all instance variables.

-   Every public method has Args:, Returns:, Raises:, and Example:
    sections in Google docstring format.

-   No TODO comments left in any non-\[OPTIONAL\] code path.

-   No commented-out dead code anywhere in the project.

-   No magic numbers --- all numeric constants are named module-level
    variables with units.

-   No mutable default arguments (def f(x=\[\])) anywhere.

**14.2 Architecture**

-   The dependency graph in §5 is honoured exactly --- verify with
    \`pydeps oure/\` or grep for cross-layer imports.

-   All external I/O (HTTP, SQLite, file system) is isolated to
    \`data/\` and \`cli/\` layers only.

-   All physics computations are pure functions of StateVector and
    CovarianceMatrix --- no I/O side effects.

-   The CLI handles all user-facing error messages --- physics layers
    raise exceptions, never print or exit.

**14.3 Testing**

-   Every file in \`oure/\` has a corresponding test file in
    \`tests/unit/\`.

-   Test functions test one thing --- no test tests multiple behaviours.

-   Tests never call real external APIs --- all network calls are
    monkeypatched.

-   Numerical tests use \`np.testing.assert_allclose\` with documented
    tolerances, not bare \`==\`.

-   Tests are deterministic --- any randomness uses a fixed seed from
    \`conftest.py\` fixture.

**14.4 Security**

-   No credentials stored in source code --- all via environment
    variables or \`.env\` file (never committed).

-   \`.env\` and \`\*.db\` are in \`.gitignore\`.

-   SQL queries use parameterized \`?\` placeholders --- no f-string SQL
    construction anywhere.

-   API responses are validated through Pydantic schemas before being
    converted to domain models.

**14.5 README Requirements**

-   Installation: \`pip install oure-risk-engine\` and \`pip install -e
    \'.\[dev\]\'\`

-   Quick Start: complete working example with fake credentials and ISS
    TLE

-   Command reference: all subcommands with their options

-   Architecture diagram: ASCII art of the layer structure

-   Physics references: citations for SGP4, J2, Foster\'s algorithm

-   Contributing guide: how to run tests, lint, and submit PRs

*End of OURE Agentic Build Specification · v1.0*

All specifications are self-contained. Agent may proceed without
external references.
