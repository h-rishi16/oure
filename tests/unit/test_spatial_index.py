import numpy as np
import pytest

from oure.conjunction.spatial_index import KDTreeSpatialIndex


def test_kd_tree_spatial_index():
    # 1. Setup
    positions = np.array(
        [
            [7000.0, 0.0, 0.0],
            [7001.0, 0.0, 0.0],
            [7005.0, 0.0, 0.0],
            [0.0, 7000.0, 0.0],
        ]
    )

    index = KDTreeSpatialIndex(positions)

    # 2. Test radius query
    # Should find indices 0 and 1
    close_indices = index.query_radius(np.array([7000.0, 0.0, 0.0]), radius_km=2.0)
    assert len(close_indices) == 2
    assert 0 in close_indices
    assert 1 in close_indices
    assert 2 not in close_indices

    # 3. Test k-nearest query
    distances, indices = index.query_k_nearest(np.array([7000.0, 0.0, 0.0]), k=2)
    assert len(distances) == 2
    assert indices[0] == 0
    assert indices[1] == 1
    assert distances[0] == 0.0
    assert distances[1] == 1.0

    # 4. Test size
    assert index.size == 4

    # 5. Test error handling
    with pytest.raises(ValueError):
        KDTreeSpatialIndex(np.array([1, 2, 3]))  # Wrong shape
