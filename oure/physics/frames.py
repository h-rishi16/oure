"""
OURE Physics Engine - Coordinate Frame Transformations
====================================================
"""

import numpy as np

from oure.core import constants


def rv2coe_vectorized(r: np.ndarray, v: np.ndarray, mu: float = constants.MU_KM3_S2) -> tuple[np.ndarray, ...]:
    """
    Converts state vectors to classical orbital elements, vectorized.
    
    Args:
        r: Position vectors, shape (n, 3)
        v: Velocity vectors, shape (n, 3)
        mu: Standard gravitational parameter (km^3/s^2).
    
    Returns:
        A tuple of numpy arrays (a, ecc, incl, raan, argp, nu)
    """
    r = np.atleast_2d(r)
    v = np.atleast_2d(v)
    mag_r = np.linalg.norm(r, axis=1)
    mag_v = np.linalg.norm(v, axis=1)
    h = np.cross(r, v)
    mag_h = np.linalg.norm(h, axis=1)
    e_vec = np.cross(v, h) / mu - r / mag_r[:, np.newaxis]
    ecc = np.linalg.norm(e_vec, axis=1)
    incl = np.arccos(h[:, 2] / mag_h)
    n_vec = np.cross([0, 0, 1], h)
    mag_n = np.linalg.norm(n_vec, axis=1)
    raan = np.arccos(n_vec[:, 0] / mag_n)
    raan[n_vec[:, 1] < 0] = 2 * np.pi - raan[n_vec[:, 1] < 0]
    argp = np.arccos(np.einsum('ij,ij->i', n_vec, e_vec) / (mag_n * ecc))
    argp[e_vec[:, 2] < 0] = 2 * np.pi - argp[e_vec[:, 2] < 0]
    nu = np.arccos(np.einsum('ij,ij->i', e_vec, r) / (ecc * mag_r))
    nu[np.einsum('ij,ij->i', r, v) < 0] = 2 * np.pi - nu[np.einsum('ij,ij->i', r, v) < 0]
    a = 1 / (2 / mag_r - mag_v**2 / mu)
    return a, ecc, incl, raan, argp, nu
