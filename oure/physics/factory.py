"""
OURE Physics Engine - Propagator Factory
========================================
"""

from __future__ import annotations

import logging

from oure.core.constants import SOLAR_FLUX_MEAN_SFU
from oure.core.models import TLERecord

from .base import BasePropagator
from .drag_corrector import AtmosphericDragCorrector
from .j2_corrector import J2PerturbationCorrector
from .sgp4_propagator import SGP4Propagator

logger = logging.getLogger("oure.physics.factory")

class PropagatorFactory:
    """
    Assembles the layered propagator chain from a TLE + space weather context.
    """

    @staticmethod
    def build(
        tle: TLERecord,
        solar_flux: float = SOLAR_FLUX_MEAN_SFU,
        include_j2: bool = False,
        include_drag: bool = True,
        cd: float = 2.2,
        area_m2: float = 10.0,
        mass_kg: float = 500.0,
    ) -> BasePropagator:
        """
        Builds and returns the configured propagator chain.
        """
        chain: BasePropagator = SGP4Propagator.from_tle(tle)

        if include_j2:
            chain = J2PerturbationCorrector(chain)
            logger.debug("J2 perturbation layer enabled")

        if include_drag:
            chain = AtmosphericDragCorrector(
                chain, cd=cd, area_m2=area_m2,
                mass_kg=mass_kg, solar_flux=solar_flux
            )
            logger.debug(f"Atmospheric drag layer enabled (F10.7={solar_flux})")

        return chain
