"""
OURE Conjunction Assessment - KD-Tree Spatial Index
===================================================
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import KDTree


class KDTreeSpatialIndex:
    """
    KD-Tree wrapper for fast satellite proximity queries.
    Reduces O(N²) pairwise screening to O(N log N) per timestep.
    """

    def __init__(self, positions: np.ndarray):
        """
        Initializes the spatial index with a set of positions.

        Args:
            positions (np.ndarray): Array of shape (N, 3) of ECI positions in km.
        """
        if (
            not isinstance(positions, np.ndarray)
            or positions.ndim != 2
            or positions.shape[1] != 3
        ):
            raise ValueError("Input 'positions' must be a NumPy array of shape (N, 3)")
        self._tree = KDTree(positions)

    def query_radius(self, point: np.ndarray, radius_km: float) -> list[int]:
        """
        Queries the index for all points within a given radius of a point.

        Args:
            point (np.ndarray): The center point of the query sphere, shape (3,).
            radius_km (float): The radius of the query sphere in km.

        Returns:
            List[int]: A list of indices into the original positions array.
        """
        return list(self._tree.query_ball_point(point, r=radius_km))

    def query_k_nearest(
        self, point: np.ndarray, k: int
    ) -> tuple[list[float], list[int]]:
        """
        Queries the index for the k-nearest neighbors to a point.

        Args:
            point (np.ndarray): The point to query, shape (3,).
            k (int): The number of nearest neighbors to find.

        Returns:
            A tuple containing:
            - A list of distances to the neighbors.
            - A list of indices of the neighbors.
        """
        distances, indices = self._tree.query(point, k=k)
        if isinstance(distances, float):
            return [distances], [int(indices)]
        return distances.tolist(), indices.tolist()  # type: ignore[return-value]

    @property
    def size(self) -> int:
        """Returns the number of points in the index."""
        return int(self._tree.n)
