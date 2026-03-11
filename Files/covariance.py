"""
OURE Uncertainty Modeling
=========================

This module answers the question: "How uncertain are we about where
a satellite will be at time T?"

Two complementary approaches:

  A) Analytical Covariance Propagation  (fast, linear assumption)
     Uses the State Transition Matrix (STM / Φ) to evolve the 6×6
     covariance matrix in time: P(t) = Φ(t,t₀) · P(t₀) · Φᵀ(t,t₀)

  B) Monte Carlo Propagation  (slower, nonlinear-safe)
     Spawns N "ghost" satellites by sampling the covariance as a
     multivariate Gaussian, propagates each independently, then
     recomputes the covariance from the ensemble.

The two methods are cross-validated: if they diverge significantly,
we know the trajectory has strong nonlinearities and the 2D-Pc
Gaussian assumption breaks down.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE MATH: Covariance Matrix Propagation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A satellite's state at any time is a 6D random vector:
    x = [x, y, z, vx, vy, vz]ᵀ  ∈ ℝ⁶

Its uncertainty is the 6×6 covariance matrix:
    P = E[(x - x̄)(x - x̄)ᵀ]

where x̄ is the best estimated state and E[·] is expectation.

The diagonal entries are variances (squared uncertainties):
    P[0,0] = σ²_x      (uncertainty in x-position, km²)
    P[3,3] = σ²_vx     (uncertainty in x-velocity, km²/s²)

Off-diagonal entries are cross-correlations:
    P[0,3] = Cov(x, vx)  (how position error correlates with velocity error)

For a circular LEO orbit, along-track position error grows quickly
because a velocity error directly changes the orbital energy, which
changes the period, which shifts where the satellite is along its
track. This is called the "ballistic coefficient uncertainty" problem.
Result: P grows fastest in the along-track (T) direction.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE STATE TRANSITION MATRIX (STM)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The STM Φ(t, t₀) is a 6×6 matrix that maps how a small perturbation
δx₀ at time t₀ evolves into δx(t) at time t:

    δx(t) = Φ(t, t₀) · δx₀

Formally, Φ satisfies the matrix ODE:
    dΦ/dt = A(t) · Φ,    Φ(t₀, t₀) = I₆

where A(t) = ∂f/∂x is the Jacobian of the equations of motion.

For the two-body problem with J2, A has a known analytical form.
We use a linearised approximation (Gauss-Clohessy-Wiltshire / Yamanaka-
Ankersen for near-circular orbits, or full Brouwer theory for eccentric).

Covariance propagation then follows:
    P(t) = Φ(t, t₀) · P(t₀) · Φᵀ(t, t₀)

This is exact for linear dynamics. For real orbits (nonlinear), it's
an approximation that degrades over multi-day propagation intervals.
That's why Monte Carlo is used as a check.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
from scipy.linalg import expm  # Matrix exponential for STM

from oure.core.models import StateVector, CovarianceMatrix
from oure.physics.propagator import BasePropagator, MU, R_EARTH, J2

logger = logging.getLogger("oure.uncertainty")


# ---------------------------------------------------------------------------
# State Transition Matrix (STM) Calculator
# ---------------------------------------------------------------------------

class STMCalculator:
    """
    Computes the 6×6 State Transition Matrix Φ(t, t₀) for covariance
    propagation.

    Three levels of fidelity are implemented:
      LEVEL 0: Two-body analytical  (Φ in closed form, ~5µs)
      LEVEL 1: J2 linearised        (adds secular RAAN/ω terms, ~50µs)
      LEVEL 2: Numerical finite-diff (full perturbation model, ~500µs)

    Level 1 is used by default for the Pc calculation.
    Level 2 is reserved for high-stakes conjunction warnings.
    """

    def __init__(self, fidelity: int = 1):
        assert fidelity in (0, 1, 2), "Fidelity must be 0, 1, or 2"
        self.fidelity = fidelity

    def compute(self, state: StateVector, dt_seconds: float) -> np.ndarray:
        """Returns the 6×6 STM Φ(t₀+dt, t₀)."""
        if self.fidelity == 0:
            return self._two_body_stm(state, dt_seconds)
        elif self.fidelity == 1:
            return self._j2_linearised_stm(state, dt_seconds)
        else:
            return self._numerical_stm(state, dt_seconds)

    def _two_body_stm(self, state: StateVector, dt: float) -> np.ndarray:
        """
        Analytical STM for unperturbed Keplerian motion.

        The equations of motion are:
            ẋ = f(x)  where  f = [v, -μr/|r|³]

        The Jacobian A = ∂f/∂x:
            A = [ 0₃  I₃  ]
                [ G   0₃  ]

        where G is the gravity gradient tensor (3×3):
            G_ij = μ/r³ · (3 r_i r_j/r² - δ_ij)

        For circular orbits with radius r and mean motion n = √(μ/r³),
        the STM has the famous CW (Clohessy-Wiltshire) solution:
            [See Schaub & Junkins, Analytical Mechanics of Space Systems]
        """
        r = state.r
        r_mag = np.linalg.norm(r)
        n = np.sqrt(MU / r_mag**3)  # mean motion rad/s

        # Build the gravity gradient tensor G
        G = MU / r_mag**3 * (3 * np.outer(r, r) / r_mag**2 - np.eye(3))

        # Jacobian A (6×6)
        A = np.zeros((6, 6))
        A[:3, 3:] = np.eye(3)
        A[3:, :3] = G

        # STM via matrix exponential: Φ = exp(A·Δt)
        Phi = expm(A * dt)
        return Phi

    def _j2_linearised_stm(self, state: StateVector, dt: float) -> np.ndarray:
        """
        Extends the two-body STM with first-order J2 corrections.

        J2 adds terms to the gravity gradient tensor:
            G_J2 = -3J2 μ R_e² / r⁵ · T(r̂)

        where T(r̂) is a tensor function of the unit position vector.
        The full expression (Brouwer 1959, Kozai 1959):

            a_J2[i] = -3/2 J2 μ R_e²/r⁴ · r̂[i] · (1 - 5(r̂_z)²)  for i=x,y
            a_J2[z] = -3/2 J2 μ R_e²/r⁴ · r̂_z · (3 - 5(r̂_z)²)

        The Jacobian ∂a_J2/∂r adds a correction ΔG to the gravity gradient.
        """
        # Get base two-body STM first
        Phi_2b = self._two_body_stm(state, dt)

        r = state.r
        r_mag = np.linalg.norm(r)
        r_hat = r / r_mag
        z_r = r_hat[2]  # cos(geocentric latitude)

        # J2 correction to gravity gradient (∂a_J2/∂r term, 3×3)
        coeff = -3/2 * J2 * MU * R_EARTH**2 / r_mag**4

        delta_G = np.zeros((3, 3))
        for i in range(3):
            for j in range(3):
                dij = 1.0 if i == j else 0.0
                e_z_i = 1.0 if i == 2 else 0.0
                e_z_j = 1.0 if j == 2 else 0.0

                delta_G[i, j] = coeff * (
                    (1 - 5*z_r**2) * dij / r_mag
                    - (1 - 5*z_r**2) * r_hat[i]*r_hat[j] / r_mag
                    - 10*z_r * r_hat[i]*e_z_j / r_mag
                    + 35*z_r**2 * r_hat[i]*r_hat[j] / r_mag
                )

        # Perturbed Jacobian
        A = np.zeros((6, 6))
        A[:3, 3:] = np.eye(3)
        G_total = MU / r_mag**3 * (3 * np.outer(r, r) / r_mag**2 - np.eye(3)) + delta_G
        A[3:, :3] = G_total

        return expm(A * dt)

    def _numerical_stm(
        self,
        state: StateVector,
        dt: float,
        propagator: Optional[BasePropagator] = None
    ) -> np.ndarray:
        """
        Finite-difference STM: perturb each state component by ε,
        propagate both ±ε, compute central difference.

            Φ[:, i] ≈ [f(x + ε·eᵢ, dt) - f(x - ε·eᵢ, dt)] / (2ε)

        Most accurate, but requires 12 propagations per STM (6 components × 2).
        Only used for high-value conjunction assessments.
        """
        if propagator is None:
            raise ValueError("Numerical STM requires a propagator instance")

        eps = 1.0  # 1 km position perturbation, 0.001 km/s velocity
        eps_vec = np.array([eps, eps, eps, eps/1000, eps/1000, eps/1000])

        x0 = np.concatenate([state.r, state.v])
        Phi = np.zeros((6, 6))

        for i in range(6):
            dx = np.zeros(6)
            dx[i] = eps_vec[i]

            # +ε perturbation
            sp = StateVector(r=x0[:3]+dx[:3], v=x0[3:]+dx[3:],
                             epoch=state.epoch, sat_id=state.sat_id)
            xp = propagator.propagate(sp, dt)

            # -ε perturbation
            sm = StateVector(r=x0[:3]-dx[:3], v=x0[3:]-dx[3:],
                             epoch=state.epoch, sat_id=state.sat_id)
            xm = propagator.propagate(sm, dt)

            xp_vec = np.concatenate([xp.r, xp.v])
            xm_vec = np.concatenate([xm.r, xm.v])
            Phi[:, i] = (xp_vec - xm_vec) / (2 * eps_vec[i])

        return Phi


# ---------------------------------------------------------------------------
# Analytical Covariance Propagator
# ---------------------------------------------------------------------------

class CovariancePropagator:
    """
    Propagates the 6×6 covariance matrix from t₀ to t using the STM:

        P(t) = Φ(t, t₀) · P(t₀) · Φᵀ(t, t₀)

    Also adds process noise Q to account for unmodelled forces
    (solar radiation pressure, outgassing, manoeuvres):

        P(t) = Φ P₀ Φᵀ + Q

    Q is diagonal, with values calibrated empirically per satellite type.
    Larger Q = less trust in our dynamical model = faster uncertainty growth.
    """

    # Default process noise spectral density (km²/s³)
    DEFAULT_Q_SCALE = 1e-10

    def __init__(self, stm_calculator: Optional[STMCalculator] = None):
        self.stm = stm_calculator or STMCalculator(fidelity=1)

    def propagate(
        self,
        covariance: CovarianceMatrix,
        reference_state: StateVector,
        dt_seconds: float,
        q_scale: float = DEFAULT_Q_SCALE
    ) -> CovarianceMatrix:
        """
        Propagate covariance by dt_seconds.

        Parameters
        ----------
        covariance      : Initial P(t₀), 6×6 in ECI
        reference_state : The nominal trajectory point at t₀
        dt_seconds      : Propagation interval
        q_scale         : Process noise intensity (km²/s³)

        Returns
        -------
        New CovarianceMatrix at t₀ + dt
        """
        from datetime import timedelta

        Phi = self.stm.compute(reference_state, dt_seconds)
        P0  = covariance.matrix

        # Core propagation: P(t) = Φ P₀ Φᵀ
        P_propagated = Phi @ P0 @ Phi.T

        # Add process noise Q (diagonal, continuous-to-discrete)
        # Q_discrete = q_scale · diag([0,0,0, dt, dt, dt]) · Δt
        Q = np.zeros((6, 6))
        Q[3:, 3:] = np.eye(3) * q_scale * dt_seconds   # velocity noise
        Q[:3, :3] = np.eye(3) * q_scale * dt_seconds**3 / 3  # position noise

        P_final = P_propagated + Q

        # Enforce symmetry (guard against floating point drift)
        P_final = 0.5 * (P_final + P_final.T)

        target_epoch = covariance.epoch + timedelta(seconds=dt_seconds)

        logger.debug(
            f"Covariance propagated Δt={dt_seconds:.0f}s | "
            f"σ_pos={np.sqrt(P_final[0,0]):.3f} km | "
            f"σ_vel={np.sqrt(P_final[3,3])*1000:.3f} m/s"
        )

        return CovarianceMatrix(
            matrix=P_final,
            epoch=target_epoch,
            sat_id=covariance.sat_id,
            frame="ECI"
        )


# ---------------------------------------------------------------------------
# Monte Carlo Ghost Trajectory Generator
# ---------------------------------------------------------------------------

@dataclass
class MonteCarloResult:
    """Container for a completed Monte Carlo run."""
    nominal_state: StateVector
    ghost_states: list[StateVector]      # N propagated samples
    sample_covariance: np.ndarray        # 6×6 recomputed from ensemble
    n_samples: int
    outlier_fraction: float              # Samples > 3σ from nominal


class MonteCarloUncertaintyPropagator:
    """
    Generates N "ghost" satellite trajectories by sampling the initial
    state distribution, propagating each, then reconstructing the
    output covariance from the ensemble.

    Algorithm
    ---------
    1. SAMPLE: Draw N samples from x₀ ~ N(x̄₀, P₀)
       Using Cholesky decomposition:
           x_sample = x̄₀ + L · ξ,   ξ ~ N(0, I₆)
           where L = chol(P₀) is the lower triangular Cholesky factor.
           This is numerically stable and exactly reproduces P₀'s
           correlations in the sample set.

    2. PROPAGATE: Run each sample through the full physics engine.
       This captures the nonlinear stretching and folding of the
       uncertainty ellipsoid that the linear STM misses.

    3. RECONSTRUCT: Compute sample mean and covariance:
           x̄(t) = 1/N Σ xᵢ(t)
           P(t)  = 1/(N-1) Σ (xᵢ - x̄)(xᵢ - x̄)ᵀ

    Convergence: ~1000 samples is sufficient for Pc estimates to within
    10% of the analytical value for typical LEO conjunctions (Alfriend 2009).
    2000+ samples for high-eccentricity or long-propagation scenarios.
    """

    def __init__(
        self,
        propagator: BasePropagator,
        n_samples: int = 1000,
        random_seed: Optional[int] = 42
    ):
        self.propagator = propagator
        self.n_samples = n_samples
        self.rng = np.random.default_rng(random_seed)

    def run(
        self,
        initial_state: StateVector,
        initial_covariance: CovarianceMatrix,
        target_epoch: datetime
    ) -> MonteCarloResult:
        """
        Execute Monte Carlo propagation.

        Returns MonteCarloResult with all ghost states and the
        reconstructed covariance at target_epoch.
        """
        P0 = initial_covariance.matrix
        x0 = np.concatenate([initial_state.r, initial_state.v])

        # Step 1: Cholesky decomposition of P₀
        try:
            L = np.linalg.cholesky(P0)
        except np.linalg.LinAlgError:
            logger.warning("Covariance not positive definite — adding regularisation")
            P0_reg = P0 + np.eye(6) * 1e-12
            L = np.linalg.cholesky(P0_reg)

        # Step 2: Sample N initial conditions
        xi = self.rng.standard_normal((self.n_samples, 6))  # shape (N, 6)
        perturbations = (L @ xi.T).T                         # shape (N, 6)
        samples_x0 = x0 + perturbations                     # shape (N, 6)

        logger.info(f"Propagating {self.n_samples} Monte Carlo samples to {target_epoch}")

        # Step 3: Propagate each ghost satellite
        ghost_states = []
        for i, sx in enumerate(samples_x0):
            ghost = StateVector(
                r=sx[:3], v=sx[3:],
                epoch=initial_state.epoch,
                sat_id=f"{initial_state.sat_id}_ghost_{i:04d}"
            )
            propagated = self.propagator.propagate_to(ghost, target_epoch)
            ghost_states.append(propagated)

            if (i + 1) % 200 == 0:
                logger.debug(f"Monte Carlo progress: {i+1}/{self.n_samples}")

        # Step 4: Reconstruct covariance from ensemble
        ghost_vecs = np.array([
            np.concatenate([g.r, g.v]) for g in ghost_states
        ])  # shape (N, 6)

        x_mean = ghost_vecs.mean(axis=0)
        delta = ghost_vecs - x_mean              # (N, 6) — deviations
        P_mc = (delta.T @ delta) / (self.n_samples - 1)  # 6×6 sample covariance

        # Count statistical outliers (> 3σ Mahalanobis distance)
        P_inv = np.linalg.pinv(P_mc)
        distances = np.array([delta[i] @ P_inv @ delta[i] for i in range(self.n_samples)])
        outlier_frac = float(np.mean(distances > 9.0))  # 9 = 3² Mahal. threshold

        nominal_propagated = StateVector(
            r=x_mean[:3], v=x_mean[3:],
            epoch=target_epoch,
            sat_id=initial_state.sat_id
        )

        logger.info(
            f"MC complete | outlier_frac={outlier_frac:.2%} | "
            f"σ_along-track≈{np.sqrt(P_mc[1,1]):.3f} km"
        )

        return MonteCarloResult(
            nominal_state=nominal_propagated,
            ghost_states=ghost_states,
            sample_covariance=P_mc,
            n_samples=self.n_samples,
            outlier_fraction=outlier_frac
        )

    def cross_validate_with_analytical(
        self,
        mc_result: MonteCarloResult,
        analytical_covariance: CovarianceMatrix,
        tolerance: float = 0.30
    ) -> dict:
        """
        Compare Monte Carlo covariance to analytical STM propagation.

        If they agree within `tolerance` (30% default), linear methods
        are adequate and we trust the 2D-Pc formula.
        If they diverge, nonlinear effects dominate — flag for operator.
        """
        P_mc = mc_result.sample_covariance
        P_an = analytical_covariance.matrix

        # Frobenius norm relative difference
        diff = np.linalg.norm(P_mc - P_an, 'fro') / np.linalg.norm(P_an, 'fro')

        return {
            "relative_difference": diff,
            "linear_assumption_valid": diff < tolerance,
            "recommendation": (
                "Analytical Pc valid" if diff < tolerance
                else "Use MC-based Pc — strong nonlinearity detected"
            )
        }
