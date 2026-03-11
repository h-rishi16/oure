"""
OURE Data Ingestion Layer - Schemas
===================================
Pydantic schemas for data validation.
"""

from datetime import datetime

from pydantic import BaseModel


class TLERecordSchema(BaseModel):
    NORAD_CAT_ID: str
    OBJECT_NAME: str
    TLE_LINE1: str
    TLE_LINE2: str
    EPOCH: datetime
    INCLINATION: float
    RA_OF_ASC_NODE: float
    ECCENTRICITY: float
    ARG_OF_PERICENTER: float
    MEAN_ANOMALY: float
    MEAN_MOTION: float
    BSTAR: float

class SolarFluxSchema(BaseModel):
    Flux: float
    TimeStamp: datetime
