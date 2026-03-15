import numpy as np
import pytest

from oure.core.exceptions import KeplerConvergenceError
from oure.physics.kepler import solve_kepler_vectorized


def test_kepler_convergence_error():
    """Test that the Kepler solver raises an error when it fails to converge."""
    # M near pi, e very close to 1
    M = np.array([3.14])
    e = np.array([0.999999])

    # Force non-convergence by limiting iterations to 1
    with pytest.raises(KeplerConvergenceError):
        solve_kepler_vectorized(M, e, max_iter=1)
