import os
import tempfile

from celery.result import AsyncResult
from fastapi import FastAPI, File, HTTPException, UploadFile
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field, validator

from oure.api.celery_app import celery_app
from oure.api.tasks import run_fleet_screening
from oure.data.cdm_parser import CDMParser
from oure.risk.calculator import RiskCalculator

app = FastAPI(
    title="OURE API",
    version="1.0.0",
    description="Orbital Uncertainty & Risk Engine API",
)

# Instrument the app for Prometheus monitoring
Instrumentator().instrument(app).expose(app)


class RiskResponse(BaseModel):
    primary_id: str
    secondary_id: str
    tca: str
    pc: float
    warning_level: str
    miss_distance_km: float
    rel_velocity_km_s: float


class TaskSubmitRequest(BaseModel):
    primary_id: str
    secondary_ids: list[str] = Field(..., max_length=1000)

    @validator("secondary_ids")
    def limit_ids(cls, v: list[str]) -> list[str]:
        if len(v) > 1000:
            raise ValueError("Maximum 1,000 secondary IDs per screening task.")
        return v


@app.get("/health")
def health_check() -> dict[str, str]:
    """Verify the API is running."""
    return {"status": "operational", "version": "1.0.0"}


@app.post("/tasks/screen")
def submit_screening_task(req: TaskSubmitRequest) -> dict[str, str]:
    """Submit a fleet screening job to the background Celery worker queue."""
    task = run_fleet_screening.delay(req.primary_id, req.secondary_ids)
    return {"task_id": str(task.id), "status": "submitted"}


@app.get("/tasks/{task_id}")
def get_task_status(task_id: str) -> dict[str, object]:
    """Retrieve the status and results of a background Celery task."""
    task_result = AsyncResult(task_id, app=celery_app)
    response: dict[str, object] = {
        "task_id": task_id,
        "state": task_result.state,
    }

    if task_result.state == "PROGRESS":
        response["meta"] = task_result.info
    elif task_result.state == "SUCCESS":
        response["result"] = task_result.result
    elif task_result.state == "FAILURE":
        response["error"] = str(task_result.info)

    return response


@app.post("/analyze/cdm", response_model=RiskResponse)
async def analyze_cdm(
    file: UploadFile = File(...), hard_body_radius: float = 20.0
) -> RiskResponse:
    """
    Upload a JSON CDM file and receive a risk assessment.
    """
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON CDMs are supported.")

    temp_path = None
    try:
        # Create temp file inside the try block to ensure cleanup
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
            temp_path = temp_file.name
            contents = await file.read()
            temp_file.write(contents)

        # Parse and calculate
        event = CDMParser.parse_json(temp_path)
        calc = RiskCalculator(hard_body_radius_m=hard_body_radius)
        result = calc.compute_pc(event)

        return RiskResponse(
            primary_id=result.conjunction.primary_id,
            secondary_id=result.conjunction.secondary_id,
            tca=result.conjunction.tca.isoformat(),
            pc=result.pc,
            warning_level=result.warning_level,
            miss_distance_km=result.conjunction.miss_distance_km,
            rel_velocity_km_s=result.conjunction.relative_velocity_km_s,
        )
    except Exception:
        import logging

        logging.getLogger("oure.api").exception("CDM processing failed")
        raise HTTPException(
            status_code=500,
            detail="Failed to parse CDM file. Ensure it follows the CCSDS JSON schema.",
        )
    finally:
        # Guaranteed cleanup regardless of where an exception occurred
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
