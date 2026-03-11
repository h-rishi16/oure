"""
OURE Data Ingestion Layer - CCSDS CDM Parser
============================================
"""

import json
from datetime import datetime, timezone
import numpy as np

from oure.core.models import StateVector, CovarianceMatrix, ConjunctionEvent

class CDMParser:
    """
    Parses official CCSDS Conjunction Data Messages (CDM) in JSON format.
    Allows OURE to ingest high-fidelity Space Force covariance matrices
    directly instead of relying on SGP4 propagation.
    """

    @staticmethod
    def parse_json(filepath: str) -> ConjunctionEvent:
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        body = data.get("body", {})
        segment1 = body.get("segment1", {})
        segment2 = body.get("segment2", {})
        
        tca_str = body.get("TCA")
        if tca_str:
            tca = datetime.fromisoformat(tca_str.replace("Z", "+00:00"))
        else:
            tca = datetime.now(timezone.utc)
            
        miss_dist = body.get("MISS_DISTANCE", 0.0)
        v_rel = body.get("RELATIVE_SPEED", 0.0)
        
        def _parse_state_cov(segment):
            meta = segment.get("metadata", {})
            data_sec = segment.get("data", {})
            sat_id = meta.get("OBJECT_DESIGNATOR", "UNKNOWN")
            
            state_dict = data_sec.get("state_vector", {})
            r = np.array([state_dict.get("X", 0.0), state_dict.get("Y", 0.0), state_dict.get("Z", 0.0)])
            v = np.array([state_dict.get("X_DOT", 0.0), state_dict.get("Y_DOT", 0.0), state_dict.get("Z_DOT", 0.0)])
            
            cov_dict = data_sec.get("covariance_matrix", {})
            cov = np.zeros((6, 6))
            
            # Map standard CCSDS covariance elements (CR11, CR21, etc.)
            keys = [
                ("CR11", 0, 0), ("CR21", 1, 0), ("CR22", 1, 1), 
                ("CR31", 2, 0), ("CR32", 2, 1), ("CR33", 2, 2),
                ("CR41", 3, 0), ("CR42", 3, 1), ("CR43", 3, 2), ("CR44", 3, 3),
                ("CR51", 4, 0), ("CR52", 4, 1), ("CR53", 4, 2), ("CR54", 4, 3), ("CR55", 4, 4),
                ("CR61", 5, 0), ("CR62", 5, 1), ("CR63", 5, 2), ("CR64", 5, 3), ("CR65", 5, 4), ("CR66", 5, 5)
            ]
            for k, i, j in keys:
                val = cov_dict.get(k, 0.0)
                cov[i, j] = val
                if i != j:
                    cov[j, i] = val # Symmetric
                    
            # If no covariance is provided in CDM, fallback to identity
            if np.all(cov == 0):
                cov = np.diag([1.0, 1.0, 1.0, 1e-6, 1e-6, 1e-6])
            
            state = StateVector(r=r, v=v, epoch=tca, sat_id=sat_id)
            covariance = CovarianceMatrix(matrix=cov, epoch=tca, sat_id=sat_id)
            return sat_id, state, covariance
            
        id1, state1, cov1 = _parse_state_cov(segment1)
        id2, state2, cov2 = _parse_state_cov(segment2)
        
        return ConjunctionEvent(
            primary_id=id1, secondary_id=id2,
            tca=tca, miss_distance_km=miss_dist, relative_velocity_km_s=v_rel,
            primary_state=state1, secondary_state=state2,
            primary_covariance=cov1, secondary_covariance=cov2
        )