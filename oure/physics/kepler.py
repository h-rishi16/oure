"""
OURE Physics Engine - Kepler Solver
===================================
"""

import numpy as np

from oure.core.exceptions import KeplerConvergenceError


def solve_kepler_vectorized(
    M: np.ndarray, e: np.ndarray, tol: float = 1e-12, max_iter: int = 50
) -> np.ndarray:
    """
    Solves Kepler's equation M = E - e*sin(E) for the eccentric anomaly E,
    using the Newton-Raphson method in a vectorized manner.

    Args:
        M: Mean anomaly in radians.
        e: Eccentricity (0 <= e < 1).
        tol: Tolerance for convergence.
        max_iter: Maximum number of iterations.

    Returns:
        Eccentric anomaly E in radians.

    Raises:
        KeplerConvergenceError: If the solver fails to converge.
    """
    E = M.copy()
    for i in range(max_iter):
        f = E - e * np.sin(E) - M
        f_prime = 1 - e * np.cos(E)

        # Avoid division by zero for near-parabolic orbits
        f_prime[f_prime < 1e-12] = 1e-12

        delta_E = f / f_prime
        E -= delta_E

        if np.all(np.abs(delta_E) < tol):
            return E

    raise KeplerConvergenceError(
        f"Kepler solver did not converge after {max_iter} iterations."
    )
