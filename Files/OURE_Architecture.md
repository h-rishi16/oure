**OURE**

Orbital Uncertainty & Risk Engine

*Satellite Collision Probability Solver*

**Architecture & Class Design Reference**

Version 0.1.0 · Python 3.10+ · Senior Aerospace Software Engineering

**1. Project Overview**

OURE is a high-performance command-line tool for predicting the
Probability of Collision (Pc) between satellites in Low Earth Orbit
(LEO). It ingests real-time orbital data, propagates state uncertainties
using both analytical and Monte Carlo methods, and applies Foster\'s
algorithm on the B-plane to produce actionable risk assessments.

  -----------------------------------------------------------------------
  **Parameter**          **Value**
  ---------------------- ------------------------------------------------
  Accuracy Target        Pc estimates within 10% of reference for miss
                         distances 0.1--10 km

  Performance            Screen 27,000 objects in \< 30 seconds (KD-Tree
                         O(N log N))

  Latency                Full Pc pipeline (single pair) \< 200ms on
                         commodity hardware

  Languages              Python 3.10+, with sgp4, numpy, scipy, click

  Data Sources           Space-Track.org (TLE), NOAA SWPC (F10.7 solar
                         flux)

  Risk Threshold         RED ≥ 1×10⁻³ \| YELLOW ≥ 1×10⁻⁵ \| GREEN \<
                         1×10⁻⁵
  -----------------------------------------------------------------------

**2. Modular Architecture --- Separation of Concerns**

The system is divided into five strictly decoupled layers. Each layer
speaks only through the core data models defined in oure/core/models.py.
No layer imports from a layer it doesn\'t own.

**2.1 Layer Map**

  ----------------------------------------------------------------------------------
  **Module**                  **Layer**     **Responsibility**
  --------------------------- ------------- ----------------------------------------
  core/models.py              Data Models   StateVector, TLERecord,
                                            CovarianceMatrix, ConjunctionEvent,
                                            RiskResult --- immutable frozen
                                            dataclasses. Zero business logic. Every
                                            other layer depends on this.

  data/fetchers.py            Ingestion     SpaceTrackFetcher, NOAASolarFluxFetcher,
                                            CacheManager. Owns all I/O. The physics
                                            engine never calls these directly.

  physics/propagator.py       Physics       SGP4Propagator, J2PerturbationCorrector,
                              Engine        AtmosphericDragCorrector,
                                            PropagatorFactory. Decorator chain for
                                            layered perturbation models.

  uncertainty/covariance.py   Uncertainty   STMCalculator, CovariancePropagator,
                                            MonteCarloUncertaintyPropagator.
                                            Analytical STM and Monte Carlo ghost
                                            trajectories.

  conjunction/assessor.py     Risk Math     ConjunctionAssessor (KD-Tree + TCA),
                                            RiskCalculator (B-plane + Foster\'s Pc).

  cli/commands.py             Interface     Click CLI: fetch / analyze / monitor /
                                            cache subcommands.
  ----------------------------------------------------------------------------------

**2.2 Data Flow**

The analyze pipeline flows strictly top-to-bottom with no circular
dependencies:

> Space-Track API ──▶ SpaceTrackFetcher ──▶ TLERecord
>
> NOAA API ──▶ NOAASolarFluxFetcher ──▶ SolarFluxData
>
> │
>
> PropagatorFactory.build(tle, solar_flux=F10.7)
>
> SGP4Propagator ◀── J2Corrector ◀── DragCorrector
>
> │
>
> CovariancePropagator.propagate(P₀, Φ, Δt)
>
> MonteCarloUncertaintyPropagator.run(N=1000)
>
> │
>
> ConjunctionAssessor.find_conjunctions() ← KD-Tree O(N log N)
>
> │
>
> RiskCalculator.compute_pc() ← B-plane + Foster integral
>
> │
>
> RiskResult { pc, warning_level, sigma_bplane }

**3. Physics Engine --- Propagator Stack**

**3.1 SGP4 Base Propagator**

SGP4 (Simplified General Perturbations 4, Hoots & Roehrich 1980) is the
industry standard for TLE-based orbit prediction. The propagation
pipeline follows these steps:

-   Compute time since TLE epoch: tsince (minutes)

-   Apply secular drag via B\* term to update semi-major axis a

-   Apply secular J2 terms to RAAN (Ω) and arg-of-perigee (ω)

-   Update mean anomaly M = M₀ + n·Δt

-   Solve Kepler\'s Equation via Newton-Raphson: M = E − e·sin(E)

-   Convert (a, e, i, Ω, ω, ν) → ECI via PQW rotation matrix

  ------------ ----------------------------------------------------------
  **NOTE**     In production, delegate to the sgp4 PyPI library
               (Vallado\'s port) for the certified NORAD SGP4/SDP4
               formulation. The SGP4Propagator wrapper provides a clean
               StateVector-based interface over the library.

  ------------ ----------------------------------------------------------

**3.2 J2 Perturbation Layer**

Earth\'s equatorial bulge (J₂ = 1.08263 × 10⁻³) causes two secular
drifts:

RAAN precession (orbital plane rotation):

**dΩ/dt = −3/2 · J₂ · (R_E/p)² · n · cos(i)**

At ISS altitude (410 km, i = 51.6°): dΩ/dt ≈ −7.3°/day

Argument-of-perigee drift (ellipse rotation in its plane):

**dω/dt = +3/4 · J₂ · (R_E/p)² · n · (5cos²i − 1)**

Sun-synchronous orbits are designed so J₂ precession matches the solar
drift rate (\~0.9856°/day).

The J₂ acceleration in ECI Cartesian form (used for STM Jacobian
computation):

**a_J2 = −3/2 · J₂ · μ · R_E² / \|r\|⁵ · \[x(1−5z²/r²), y(1−5z²/r²),
z(3−5z²/r²)\]**

**3.3 Atmospheric Drag Layer**

Solar activity directly modulates upper-atmosphere density via heating
of the thermosphere (200--1000 km altitude). Higher F10.7 → denser
atmosphere → more drag → faster orbital decay.

Density model (exponential with solar flux correction):

**ρ(h) = ρ₀ · exp(−(h − h₀) / H) · exp(k_F · (F10.7 − 150))**

where H is the scale height (\~7--9 km in LEO) and k_F ≈ 0.003 is the
Jacchia-Roberts solar coupling constant. At F10.7 = 250 (solar max),
density at 400 km is \~10× the solar minimum value.

Drag deceleration:

**a_drag = −½ · (C_D · A/m) · ρ · v_rel² · v̂\_rel**

**4. Covariance Matrix Propagation --- The Core Math**

**4.1 What the Covariance Represents**

A satellite\'s true state is a 6D random variable x = \[x, y, z, vx, vy,
vz\]ᵀ ∈ ℝ⁶. Our knowledge uncertainty is encoded in the 6×6 covariance
matrix P:

**P = E\[(x − x̄)(x − x̄)ᵀ\]**

Diagonal entries are variances (σ²): P\[0,0\] = σ²_x (uncertainty in
x-position, km²). Off-diagonal entries are cross-correlations: P\[0,3\]
= Cov(x, vx).

  ------------ ----------------------------------------------------------
  **KEY        For LEO circular orbits, along-track position uncertainty
  INSIGHT**    grows fastest. A small velocity error changes orbital
               energy, which changes the period, which shifts the
               satellite\'s along-track position by kilometres per hour.
               This \'along-track error inflation\' is the primary driver
               of Pc uncertainty.

  ------------ ----------------------------------------------------------

**4.2 State Transition Matrix (STM)**

The STM Φ(t, t₀) is a 6×6 matrix that linearly maps how an initial state
perturbation δx₀ evolves into δx(t):

**δx(t) = Φ(t, t₀) · δx₀**

Φ satisfies the matrix ODE:

**dΦ/dt = A(t) · Φ, Φ(t₀, t₀) = I₆**

where A(t) = ∂f/∂x is the Jacobian of the equations of motion. For a
two-body orbit with J₂:

> A = \[ 0₃×₃ I₃×₃ \]
>
> \[ G_tot 0₃×₃ \]

G_tot = G_2body + ΔG_J2 is the full gravity gradient tensor. The STM is
evaluated using the matrix exponential:

**Φ(t, t₀) = exp(A · Δt)**

**4.3 Analytical Covariance Propagation**

Once Φ is known, the covariance propagates exactly for linear dynamics:

**P(t) = Φ(t, t₀) · P(t₀) · Φᵀ(t, t₀) + Q**

Q is the process noise matrix accounting for unmodelled forces (solar
radiation pressure, outgassing):

**Q = diag(q·Δt³/3, q·Δt³/3, q·Δt³/3, q·Δt, q·Δt, q·Δt)**

where q ≈ 10⁻¹⁰ km²/s³ for a well-tracked LEO satellite.

**4.4 Monte Carlo Ghost Trajectory Method**

For nonlinear orbits or multi-day propagations, the linear STM
approximation breaks down. The Monte Carlo method is the ground truth:

-   STEP 1 --- Sample: Cholesky-decompose P₀ = L·Lᵀ, then draw N
    samples:

**x_i = x̄₀ + L · ξᵢ, ξᵢ \~ N(0, I₆)**

-   STEP 2 --- Propagate: Run each \'ghost\' satellite through the full
    physics stack (SGP4 + J2 + Drag)

-   STEP 3 --- Reconstruct: Compute sample mean and covariance from the
    ensemble:

**P(t) = 1/(N−1) · Σᵢ (xᵢ(t) − x̄(t))(xᵢ(t) − x̄(t))ᵀ**

  ----------------- ----------------------------------------------------------
  **CONVERGENCE**   N=1000 samples achieves Pc estimates within 10% of the
                    analytical value for typical LEO conjunctions (Alfriend
                    2009). Use N=2000+ for high-eccentricity orbits or
                    propagation intervals exceeding 5 orbital periods.

  ----------------- ----------------------------------------------------------

**4.5 STM Fidelity Levels**

  ----------------------------------------------------------------------------
  **Fidelity**   **Compute   **Description**
                 Time**      
  -------------- ----------- -------------------------------------------------
  Level 0        \~5 µs      Two-body analytical --- exact Keplerian STM via
                             matrix exponential. Ignores all perturbations.

  Level 1        \~50 µs     J₂ linearised --- adds first-order J₂ correction
                             to gravity gradient tensor ΔG. Default for Pc
                             computation.

  Level 2        \~500 µs    Numerical finite-difference --- perturbs each
                             state component by ε, propagates ±ε. Requires 12
                             propagator calls per STM. Used for high-value RED
                             conjunctions.
  ----------------------------------------------------------------------------

**5. Conjunction Assessment Pipeline**

**5.1 KD-Tree Spatial Indexing**

Brute-force pairwise comparison of 27,000 objects at each time step
costs O(N²) ≈ 360 million operations. The KD-Tree reduces this to O(N
log N) ≈ 400,000 operations --- a 1000× speedup.

-   Build KD-Tree over all propagated satellite positions at each time
    step (30-second intervals)

-   Query each primary satellite\'s neighbourhood within the screening
    distance (default: 5 km)

-   Collect candidate pairs: any secondary that enters the 5 km sphere
    at any time step

-   Stage 2: run golden-section TCA refinement for each candidate pair

**5.2 TCA Refinement --- Golden-Section Search**

For each flagged pair, the Time of Closest Approach (TCA) is found by
minimising the scalar range function ρ(t) = \|r_p(t) − r_s(t)\| over the
flagged time window:

**t_TCA = argmin_t \|r_p(t) − r_s(t)\|**

Golden-section search converges in \~50 function evaluations to
0.1-second accuracy. Each evaluation requires one propagation call per
object (2 total per step).

**6. Risk Calculation --- B-Plane & Foster\'s Algorithm**

**6.1 The B-Plane**

The B-plane is a 2D plane centred on the primary satellite at TCA,
oriented perpendicular to the relative velocity vector v_rel. The
probability of collision is dominated by where the secondary passes in
this plane.

B-plane coordinate axes (right-handed orthonormal set):

**ξ̂ = (ŷ × v̂\_rel) / \|ŷ × v̂\_rel\|**

**ζ̂ = v̂\_rel × ξ̂**

The 3D combined position covariance C_3D = C_primary + C_secondary is
projected to 2D via the 2×3 projection matrix T = \[ξ̂, ζ̂\]ᵀ:

**C_2D = T · C_3D · Tᵀ (3×3 → 2×2)**

**6.2 Foster\'s Algorithm**

The Probability of Collision is the integral of the combined bivariate
Gaussian PDF over the collision disk of radius R (combined hard-body
radius):

**Pc = ∬\_{ξ²+ζ²≤R²} f(ξ−b_ξ, ζ−b_ζ; C_2D) dξ dζ**

where b = T·Δr is the B-plane miss vector and f is the 2D Gaussian PDF:

**f(ξ,ζ) = 1/(2π\|C_2D\|\^½) · exp(−½ \[ξ,ζ\] C_2D⁻¹ \[ξ,ζ\]ᵀ)**

OURE implements two evaluation methods:

-   Numerical dblquad (default): scipy.integrate.dblquad over ±5σ box.
    Accurate to machine precision for well-conditioned covariances.

-   Foster series (fallback): Analytical series expansion, optimal for
    the high-σ/R regime typical in conjunction screening (σ \>\> R).

  ------------------------------------------------------------------------
  **Alert    **Pc Range**       **Response Action**
  Level**                       
  ---------- ------------------ ------------------------------------------
  GREEN      Pc \< 1×10⁻⁵       Routine monitoring. No action required.

  YELLOW     1×10⁻⁵ -- 1×10⁻³   Elevated risk. Increase tracking cadence.
                                Prepare contingency manoeuvre.

  RED        Pc ≥ 1×10⁻³        Emergency. Notify operators immediately.
                                Initiate avoidance manoeuvre decision.
  ------------------------------------------------------------------------

**7. CLI Interface Reference**

OURE provides four subcommands via the click framework. Credentials are
passed via environment variables to avoid shell history exposure.

**Setup**

> export SPACETRACK_USER=your@email.com
>
> export SPACETRACK_PASS=yourpassword
>
> pip install oure

**fetch --- Download TLE and solar flux data**

> oure fetch \--sat-id 25544 \--sat-id 43205
>
> oure fetch \--all-leo \--output tle_cache.json
>
> oure fetch \--sat-id 25544 \--force-refresh

**analyze --- Run full Pc pipeline**

> oure analyze \--primary 25544 \--secondary 43205
>
> oure analyze \--primary 25544 \--secondaries-file leo.json \\
>
> \--look-ahead 72 \--mc-samples 2000

**monitor --- Continuous watch with alerts**

> oure monitor \--primary 25544 \\
>
> \--secondaries-file catalog.json \\
>
> \--alert-threshold 1e-4 \\
>
> \--interval 1800

**cache --- Manage local SQLite cache**

> oure cache \--status
>
> oure cache \--clear-tles
>
> oure cache \--clear

**8. Design Patterns & Engineering Decisions**

  ------------------------------------------------------------------------------
  **Pattern**       **Applied In**      **Rationale**
  ----------------- ------------------- ----------------------------------------
  Decorator Chain   Propagator stack    SGP4 ← J2Corrector ← DragCorrector. Each
                                        layer wraps the one below and delegates,
                                        making it trivial to add new
                                        perturbation models or substitute the
                                        base propagator.

  Anti-Corruption   Data ingestion      SpaceTrackFetcher returns only TLERecord
  Layer                                 objects. The physics layer never sees
                                        raw JSON or SQL rows. Swap the data
                                        source without touching any physics
                                        code.

  Frozen            Core models         StateVector and other models are
  Dataclasses                           frozen=True (immutable). Physics
                                        functions produce new objects rather
                                        than mutating state --- eliminates
                                        aliasing bugs.

  Strategy Pattern  STM fidelity        STMCalculator.fidelity ∈ {0,1,2} selects
                                        the computation algorithm at runtime.
                                        The CovariancePropagator is agnostic to
                                        which strategy is active.

  Factory Method    PropagatorFactory   Encapsulates the assembly of the
                                        propagator chain. Callers never need to
                                        know about internal layering order.

  Dependency        BasePropagator ABC  ConjunctionAssessor depends on
  Inversion                             BasePropagator, not SGP4Propagator. Any
                                        propagator implementation (analytical,
                                        numerical, test stub) satisfies the
                                        interface.
  ------------------------------------------------------------------------------

**9. Dependencies**

  -----------------------------------------------------------------------
  **Package**      **Role**         **Notes**
  ---------------- ---------------- -------------------------------------
  sgp4 ≥ 2.22      Orbit            Vallado\'s certified NORAD SGP4/SDP4
                   propagation      Python port

  numpy ≥ 1.24     Linear algebra   StateVectors, matrix operations,
                                    Cholesky decomposition

  scipy ≥ 1.10     Numerical math   KD-Tree, dblquad integration, matrix
                                    exponential (expm)

  click ≥ 8.1      CLI framework    Subcommands, option parsing, colour
                                    output

  requests ≥ 2.28  HTTP client      Space-Track.org and NOAA API calls

  matplotlib (opt) Visualisation    B-plane uncertainty ellipse plots
  -----------------------------------------------------------------------

*OURE Architecture Reference · v0.1.0 · Python 3.10+*
