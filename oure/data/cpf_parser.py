"""
OURE Data Ingestion Layer - NASA CDDIS CPF Parser
=================================================
Parser for Consolidated Prediction Format (CPF) files provided by NASA CDDIS.
Used for high-precision Satellite Laser Ranging (SLR) data.
"""

import logging
from datetime import UTC, datetime, timedelta

import numpy as np

from oure.core.models import StateVector

logger = logging.getLogger("oure.data.cpf_parser")


class CPFParser:
    """
    Parses NASA CDDIS CPF (Consolidated Prediction Format) files.
    """

    @staticmethod
    def parse(file_path: str, sat_id: str = "UNKNOWN") -> list[StateVector]:
        """
        Parses a CPF file and returns a list of StateVectors.
        Extracts Type 10 (Ephemeris) records.
        """
        states = []

        try:
            with open(file_path, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if not parts:
                        continue

                    # Record Type 10 = Position (and optionally velocity)
                    if parts[0] == "10":
                        try:
                            # CPF Format for Type 10:
                            # 10 0 MJD SEC_OF_DAY leap_sec x y z [vx vy vz]
                            mjd = int(parts[2])
                            sec_of_day = float(parts[3])

                            # Convert MJD to datetime
                            # MJD 0 is Nov 17, 1858
                            base_date = datetime(1858, 11, 17, tzinfo=UTC)
                            epoch = base_date + timedelta(days=mjd, seconds=sec_of_day)

                            # Positions in CPF are in meters, OURE uses km
                            x_km = float(parts[5]) / 1000.0
                            y_km = float(parts[6]) / 1000.0
                            z_km = float(parts[7]) / 1000.0

                            r = np.array([x_km, y_km, z_km])

                            # Velocities might not be present in all CPF type 10 records
                            # If missing, we approximate or assume 0 (ideal would be interpolation)
                            if len(parts) >= 11:
                                vx_km_s = float(parts[8]) / 1000.0
                                vy_km_s = float(parts[9]) / 1000.0
                                vz_km_s = float(parts[10]) / 1000.0
                                v = np.array([vx_km_s, vy_km_s, vz_km_s])
                            else:
                                v = np.zeros(3)

                            states.append(
                                StateVector(r=r, v=v, epoch=epoch, sat_id=sat_id)
                            )
                        except (ValueError, IndexError) as e:
                            logger.debug(f"Skipping malformed CPF line: {line} - {e}")

            logger.info(f"Parsed {len(states)} ephemeris records from {file_path}")
            return states

        except FileNotFoundError:
            logger.error(f"CPF file not found: {file_path}")
            raise
