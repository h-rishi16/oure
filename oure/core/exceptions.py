"""All OURE custom exceptions in one place."""

class OUREBaseError(Exception):
    """Root exception. Never raise directly."""

class PropagationError(OUREBaseError):
    """Raised when an orbit propagation fails to converge."""

class KeplerConvergenceError(PropagationError):
    """Raised when Kepler equation Newton-Raphson fails."""

class CovarianceError(OUREBaseError):
    """Raised when a covariance matrix is invalid."""

class CovarianceNotPositiveDefiniteError(CovarianceError):
    """Raised when Cholesky decomposition fails."""

class DataFetchError(OUREBaseError):
    """Raised when an external API fetch fails."""

class SpaceTrackAuthError(DataFetchError):
    """Raised when Space-Track login is rejected."""

class CacheError(OUREBaseError):
    """Raised on SQLite cache read/write failure."""

class ConjunctionAssessmentError(OUREBaseError):
    """Raised when conjunction screening fails."""

class BPlaneError(OUREBaseError):
    """Raised when B-plane construction fails (e.g. degenerate geometry)."""

class AlertThresholdError(OUREBaseError):
    """Raised on invalid alert configuration."""
