from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import tempfile
import os

from oure.data.cdm_parser import CDMParser
from oure.risk.calculator import RiskCalculator

app = FastAPI(title="OURE API", version="1.0.0", description="Orbital Uncertainty & Risk Engine API")

class RiskResponse(BaseModel):
    primary_id: str
    secondary_id: str
    tca: str
    pc: float
    warning_level: str
    miss_distance_km: float
    rel_velocity_km_s: float

@app.get("/health")
def health_check():
    """Verify the API is running."""
    return {"status": "operational", "version": "1.0.0"}

@app.post("/analyze/cdm", response_model=RiskResponse)
async def analyze_cdm(file: UploadFile = File(...), hard_body_radius: float = 20.0):
    """
    Upload a JSON CDM file and receive a risk assessment.
    """
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON CDMs are supported.")
        
    try:
        # Save uploaded file temporarily to parse it
        with tempfile.NamedNamedTemporaryFile(delete=False, suffix=".json") as temp_file:
            contents = await file.read()
            temp_file.write(contents)
            temp_path = temp_file.name
            
        # Parse and calculate
        event = CDMParser.parse_json(temp_path)
        calc = RiskCalculator(hard_body_radius_m=hard_body_radius)
        result = calc.compute_pc(event)
        
        # Cleanup
        os.unlink(temp_path)
        
        return RiskResponse(
            primary_id=result.conjunction.primary_id,
            secondary_id=result.conjunction.secondary_id,
            tca=result.conjunction.tca.isoformat(),
            pc=result.pc,
            warning_level=result.warning_level,
            miss_distance_km=result.conjunction.miss_distance_km,
            rel_velocity_km_s=result.conjunction.relative_velocity_km_s
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CDM: {str(e)}")
