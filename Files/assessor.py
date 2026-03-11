"""
OURE Conjunction Assessment & Risk Calculation
==============================================

Two modules:

  ConjunctionAssessor  — KD-Tree spatial filtering + TCA refinement
  RiskCalculator       — B-plane projection + Foster's algorithm for Pc

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE B-PLANE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The B-plane (or "Öpik plane") is a 2D plane centred on the primary
satellite at TCA, oriented perpendicular to the relative velocity vector.

Why project to 2D?
  The relative velocity at TCA is so large (0.5–15 km/s) that the
  flyby is essentially instantaneous in the encounter frame. The
  probability of collision is dominated entirely by where the secondary
  passes in the plane perpendicular to v_rel. The along-velocity
  component contributes negligibly.

B-plane coordinate axes:
  ξ̂ = ŷ_ECI × v̂_rel / |ŷ_ECI × v̂_rel|   (in the reference frame)
  ζ̂ = v̂_rel × ξ̂                           (completing right-hand set)
  η̂ = v̂_rel                                (along-velocity, integrated out)

The 3D combined covariance C_3D (6×6) is projected to the B-plane:
  C_2D = T · C_rel_pos · Tᵀ     (3×3 → 2×2)
where T = [ξ̂, ζ̂]ᵀ is the 2×3 projection matrix.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FOSTER'S ALGORITHM (2D Pc)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The probability of collision is modelled as the integral of the combined
Gaussian PDF over the collision disk (hard-body cross section):

    Pc = ∬_{D} f(ξ, ζ) dξ dζ

where D = {(ξ,ζ) : ξ² + ζ² ≤ R²} is the collision disk of radius R
(combined hard-body radius = r_primary + r_secondary) and

    f(ξ, ζ) = 1/(2π|C|^½) · exp(-½ [ξ,ζ] C_2D⁻¹ [ξ,ζ]ᵀ)

is the bivariate normal PDF.

Foster (1992) showed this integral can be evaluated as a series
expansion:

    Pc = exp(-u/2) / (σ_ξ σ_ζ) · Σₙ (u/2)ⁿ/n! · Γ(1, v/2) / Γ(n+1)

where:
    u   = d² / (2 σ̄²)      (normalised miss distance, d = B-plane miss)
    v   = R² / (2 σ_ξ σ_ζ) (normalised collision radius)
    σ̄²  = (σ_ξ² + σ_ζ²)/2  (mean B-plane sigma)

In practice, we evaluate the double integral numerically using scipy,
with Foster's series as a fast analytical fallback.
"""

from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from scipy.spatial import KDTree
from scipy.integrate import dblquad
from scipy.stats import chi2

from oure.core.models import (
    StateVector, CovarianceMatrix, ConjunctionEvent, RiskResult
)
from oure.physics.propagator import BasePropagator

logger = logging.getLogger("oure.conjunction")


# ---------------------------------------------------------------------------
# Conjunction Assessor: KD-Tree Filtering + TCA Finder
# ---------------------------------------------------------------------------

class ConjunctionAssessor:
    """
    Two-stage conjunction detection:

    STAGE 1 — Coarse filter (KD-Tree, milliseconds):
        Build a KD-Tree over all propagated satellite positions at a
        series of time steps. Query the tree for all pairs within a
        "screening distance" (typically 5–10 km for LEO).
        This reduces O(N²) pairwise comparisons to O(N log N).

    STAGE 2 — Fine filter (TCA refinement, per-pair):
        For each flagged pair, run a parabolic/golden-section search
        to find the exact Time of Closest Approach (TCA) and the
        minimum miss distance.

    Space Situational Awareness (SSA) context:
        The US Space Surveillance Network (SSN) monitors ~27,000 objects.
        Brute-force comparison = 27000² / 2 ≈ 360M pairwise checks per
        epoch. KD-Tree reduces this to ~27000 × log(27000) ≈ 400k ops.
        That's a 1000× speedup — the difference between real-time and
        a 30-minute lag.
    """

    SCREENING_DISTANCE_KM = 5.0    # Stage 1 threshold
    TCA_TIME_STEP_S = 30.0         # Step size for coarse TCA search
    TCA_REFINEMENT_TOL_S = 0.1     # TCA refinement tolerance (0.1 seconds)

    def __init__(
        self,
        screening_distance_km: float = SCREENING_DISTANCE_KM
    ):
        self.screening_distance = screening_distance_km

    def find_conjunctions(
        self,
        primary: StateVector,
        primary_cov: CovarianceMatrix,
        primary_propagator: BasePropagator,
        secondaries: list[tuple[StateVector, CovarianceMatrix, BasePropagator]],
        look_ahead_hours: float = 72.0,
        time_step_s: float = TCA_TIME_STEP_S
    ) -> list[ConjunctionEvent]:
        """
        Screen primary against all secondaries over a look-ahead window.

        Parameters
        ----------
        primary          : Primary satellite's current state
        secondaries      : List of (state, covariance, propagator) tuples
        look_ahead_hours : How far ahead to search
        time_step_s      : KD-Tree snapshot interval (seconds)

        Returns
        -------
        List of ConjunctionEvents, sorted by Pc (highest first — proxy
        from miss distance for now, exact Pc computed later)
        """
        n_steps = int(look_ahead_hours * 3600 / time_step_s)
        t0 = primary.epoch

        # Build time grid
        time_offsets = [i * time_step_s for i in range(n_steps)]

        # Propagate all objects to each time step and collect positions
        logger.info(
            f"Screening {len(secondaries)} objects over {look_ahead_hours}h "
            f"({n_steps} steps)"
        )

        candidate_pairs: dict[int, list[datetime]] = {}

        for step_idx, dt in enumerate(time_offsets):
            epoch = t0 + timedelta(seconds=dt)

            # Propagate primary
            p_state = primary_propagator.propagate_to(primary, epoch)

            # Propagate all secondaries and collect positions
            sec_positions = np.zeros((len(secondaries), 3))
            for j, (s_state, _, s_prop) in enumerate(secondaries):
                try:
                    s_prop_state = s_prop.propagate_to(s_state, epoch)
                    sec_positions[j] = s_prop_state.r
                except Exception as e:
                    logger.debug(f"Propagation failed for secondary {j}: {e}")
                    sec_positions[j] = np.array([1e9, 1e9, 1e9])  # Far away

            # KD-Tree query: find secondaries within screening distance
            tree = KDTree(sec_positions)
            close_indices = tree.query_ball_point(
                p_state.r, r=self.screening_distance
            )

            for idx in close_indices:
                if idx not in candidate_pairs:
                    candidate_pairs[idx] = []
                candidate_pairs[idx].append(epoch)

        logger.info(f"Stage 1 found {len(candidate_pairs)} candidate pairs")

        # Stage 2: Refine TCA for each candidate pair
        conjunction_events = []
        for sec_idx, flagged_epochs in candidate_pairs.items():
            s_state, s_cov, s_prop = secondaries[sec_idx]
            event = self._refine_tca(
                primary, primary_cov, primary_propagator,
                s_state, s_cov, s_prop,
                search_start=min(flagged_epochs),
                search_end=max(flagged_epochs)
            )
            if event:
                conjunction_events.append(event)

        conjunction_events.sort(key=lambda e: e.miss_distance_km)
        logger.info(f"Stage 2 produced {len(conjunction_events)} conjunction events")
        return conjunction_events

    def _refine_tca(
        self,
        p_state: StateVector, p_cov: CovarianceMatrix, p_prop: BasePropagator,
        s_state: StateVector, s_cov: CovarianceMatrix, s_prop: BasePropagator,
        search_start: datetime, search_end: datetime
    ) -> Optional[ConjunctionEvent]:
        """
        Golden-section search for Time of Closest Approach.

        The scalar objective is the range: ρ(t) = |r_p(t) - r_s(t)|
        We minimise ρ over [t_start, t_end] using golden-section,
        which requires no derivatives and converges in ~50 evaluations.

        Golden ratio: φ = (√5 - 1) / 2 ≈ 0.618
        Each iteration reduces the search interval by factor (1 - φ) ≈ 0.382
        """
        GOLDEN = (np.sqrt(5) - 1) / 2
        dt_span = (search_end - search_start).total_seconds()

        a, b = 0.0, dt_span

        for _ in range(60):   # 60 iterations → ~10⁻¹¹ relative precision
            c = b - GOLDEN * (b - a)
            d = a + GOLDEN * (b - a)

            def range_at(dt_offset: float) -> float:
                t = search_start + timedelta(seconds=dt_offset)
                rp = p_prop.propagate_to(p_state, t).r
                rs = s_prop.propagate_to(s_state, t).r
                return float(np.linalg.norm(rp - rs))

            if range_at(c) < range_at(d):
                b = d
            else:
                a = c

            if abs(b - a) < self.TCA_REFINEMENT_TOL_S:
                break

        tca_offset = (a + b) / 2.0
        tca_epoch = search_start + timedelta(seconds=tca_offset)

        # Evaluate states at TCA
        p_tca = p_prop.propagate_to(p_state, tca_epoch)
        s_tca = s_prop.propagate_to(s_state, tca_epoch)

        miss = float(np.linalg.norm(p_tca.r - s_tca.r))
        v_rel = float(np.linalg.norm(p_tca.v - s_tca.v))

        if miss > self.screening_distance * 2:
            return None   # False positive — skip

        return ConjunctionEvent(
            primary_id=p_state.sat_id,
            secondary_id=s_state.sat_id,
            tca=tca_epoch,
            miss_distance_km=miss,
            relative_velocity_km_s=v_rel,
            primary_state=p_tca,
            secondary_state=s_tca,
            primary_covariance=p_cov,
            secondary_covariance=s_cov,
        )


# ---------------------------------------------------------------------------
# Risk Calculator: B-Plane Projection + Foster's Pc Algorithm
# ---------------------------------------------------------------------------

class RiskCalculator:
    """
    Computes the Probability of Collision for a ConjunctionEvent.

    Steps:
      1. Combine the two 3×3 position covariances into one (addition rule)
      2. Rotate into the B-plane reference frame (T matrix, 2×3)
      3. Project combined covariance onto the B-plane: C_2D = T C T^T
      4. Evaluate Foster's double integral over the collision disk
    """

    # Combined hard-body radii (sum of two satellite physical radii)
    # Typical LEO satellite: 1–5 m radius; debris: 0.1–0.5 m
    DEFAULT_HARD_BODY_RADIUS_M = 20.0     # Combined radius, conservative

    def __init__(self, hard_body_radius_m: float = DEFAULT_HARD_BODY_RADIUS_M):
        self.R = hard_body_radius_m / 1000.0   # Convert to km

    def compute_pc(self, event: ConjunctionEvent) -> RiskResult:
        """
        Full Pc pipeline for one conjunction event.
        """
        # Step 1: Build B-plane basis vectors
        T, b_vec = self._build_bplane_transform(event)

        # Step 2: Combine position covariances (sum = combined uncertainty)
        C_primary  = event.primary_covariance.matrix[:3, :3]
        C_secondary = event.secondary_covariance.matrix[:3, :3]
        C_combined_3d = C_primary + C_secondary   # Uncertainty superposition

        # Step 3: Project onto B-plane: C_2D = T · C_3D · T^T  (2×2)
        C_2d = T @ C_combined_3d @ T.T

        # Step 4: B-plane miss vector (primary relative to secondary)
        b_miss = T @ b_vec    # 2D projection of miss distance vector

        # Step 5: Evaluate Foster's integral
        pc = self._foster_integral(b_miss, C_2d)

        sigma_x = np.sqrt(C_2d[0, 0])
        sigma_z = np.sqrt(C_2d[1, 1])

        return RiskResult(
            conjunction=event,
            pc=pc,
            combined_covariance=C_2d,
            hard_body_radius_m=self.R * 1000,
            b_plane_sigma_x=sigma_x,
            b_plane_sigma_z=sigma_z,
            method="Foster2D"
        )

    def _build_bplane_transform(
        self, event: ConjunctionEvent
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Construct the 2×3 B-plane projection matrix T.

        The B-plane is perpendicular to the relative velocity vector v_rel.
        We define a right-handed coordinate system in this plane.

        Reference: Alfano (1994), "A Numerical Implementation of Spherical
        Object Collision Probability"
        """
        r_p = event.primary_state.r
        r_s = event.secondary_state.r
        v_p = event.primary_state.v
        v_s = event.secondary_state.v

        # Relative position (primary relative to secondary)
        dr = r_p - r_s
        dv = v_p - v_s

        v_hat = dv / (np.linalg.norm(dv) + 1e-15)   # Along-velocity unit vector

        # Choose reference vector not parallel to v_hat
        ref = np.array([0.0, 0.0, 1.0])
        if abs(np.dot(v_hat, ref)) > 0.9:
            ref = np.array([0.0, 1.0, 0.0])

        # B-plane axes (Gram-Schmidt orthogonalization)
        xi_hat  = np.cross(ref, v_hat)
        xi_hat /= np.linalg.norm(xi_hat)
        zeta_hat = np.cross(v_hat, xi_hat)
        zeta_hat /= np.linalg.norm(zeta_hat)

        # Projection matrix: T maps 3D ECI → 2D B-plane
        T = np.array([xi_hat, zeta_hat])   # shape (2, 3)

        return T, dr

    def _foster_integral(
        self,
        b_miss: np.ndarray,
        C_2d: np.ndarray,
        n_series: int = 200,
        use_numerical: bool = True
    ) -> float:
        """
        Evaluate the probability of collision using Foster's algorithm.

        The Pc is the integral of the bivariate normal over a disk:

            Pc = ∬_{ξ²+ζ²≤R²} f(ξ-b_ξ, ζ-b_ζ; C_2d) dξ dζ

        where f is the 2D Gaussian PDF of the secondary's position
        relative to the primary in the B-plane.

        Equivalently (after centering at the miss vector):

            Pc = ∬_{‖u-b‖≤R} (1/2π|C|^½) exp(-½ uᵀ C⁻¹ u) du

        NUMERICAL METHOD (default):
            scipy.integrate.dblquad over a domain [b-5σ, b+5σ]².
            Accurate to machine precision for well-conditioned covariances.

        SERIES METHOD (fallback):
            Foster (1992) series expansion, valid when σ >> R:

            Pc ≈ A/|C|^½ · exp(-d²/2) · Σₙ (R²/2)ⁿ/(n! · ∏ eigenvalues)

            where A = πR² (collision cross section area).
        """
        sigma_x = np.sqrt(C_2d[0, 0])
        sigma_z = np.sqrt(C_2d[1, 1])

        if use_numerical:
            return self._numerical_pc(b_miss, C_2d, sigma_x, sigma_z)
        else:
            return self._foster_series_pc(b_miss, C_2d)

    def _numerical_pc(
        self,
        b: np.ndarray,
        C: np.ndarray,
        sigma_x: float,
        sigma_z: float
    ) -> float:
        """
        Direct numerical double-integration.

        Integrate over a box of ±5σ centred on the B-plane origin.
        The integrand is the 2D Gaussian PDF restricted to the collision disk.
        """
        C_inv = np.linalg.inv(C)
        det_C = np.linalg.det(C)
        norm  = 1.0 / (2 * np.pi * np.sqrt(abs(det_C)))
        R2    = self.R**2

        def integrand(zeta: float, xi: float) -> float:
            # Is this point inside the collision disk (centred at origin)?
            if xi**2 + zeta**2 > R2:
                return 0.0
            # Gaussian PDF evaluated at (xi - b_xi, zeta - b_zeta)
            u = np.array([xi - b[0], zeta - b[1]])
            return float(norm * np.exp(-0.5 * u @ C_inv @ u))

        # Integration limits: ±5σ box
        xi_lo   = -5 * sigma_x
        xi_hi   =  5 * sigma_x
        zeta_lo = lambda xi: -5 * sigma_z
        zeta_hi = lambda xi:  5 * sigma_z

        result, _ = dblquad(
            integrand, xi_lo, xi_hi, zeta_lo, zeta_hi,
            epsabs=1e-12, epsrel=1e-8
        )
        return float(np.clip(result, 0.0, 1.0))

    def _foster_series_pc(self, b: np.ndarray, C: np.ndarray) -> float:
        """
        Foster's series expansion — fast analytical approximation.
        Recommended for σ >> R (low Pc regimes typical of conjunction screening).
        """
        from math import factorial, exp
        from scipy.special import gammainc

        # Diagonalise C for eigenvalue-based computation
        eigenvalues, _ = np.linalg.eigh(C)
        lam1, lam2 = sorted(eigenvalues)

        miss_sq = float(b @ np.linalg.inv(C) @ b)
        u = miss_sq / 2.0
        v = self.R**2 / (2 * lam1)

        # Foster's series:  Pc = exp(-u) Σ_{n=0}^{N} (u^n/n!) · (1-exp(-v) Σ_{k=0}^{n} v^k/k!)
        pc = 0.0
        exp_neg_u = exp(-u)
        v_series = exp(-v)
        v_partial = 0.0

        for n in range(min(n_series, 100)):
            # Poisson weight
            weight = exp_neg_u * (u**n) / factorial(n) if u > 0 else (1.0 if n==0 else 0.0)
            # CDF of Poisson(v) up to n: incomplete gamma
            gamma_term = gammainc(n + 1, v)
            pc += weight * gamma_term

        return float(np.clip(pc * np.pi * self.R**2 / (2 * np.pi * np.sqrt(lam1 * lam2)), 0, 1))
