"""Simulation API endpoints for batch lifecycle execution."""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.simulation_service import SimulationRunner, SimulationResult

router = APIRouter()


class SimulationRunRequest(BaseModel):
    limit: Optional[int] = Field(default=100, ge=1, le=8000)
    seed: int = Field(default=42)
    all_payments: bool = Field(default=False)
    mode: str = Field(default="mock", description="mock | real")
    fast_mode: bool = Field(default=True)


@router.post("/run", response_model=SimulationResult)
def run_simulation_endpoint(
    req: SimulationRunRequest = SimulationRunRequest(),
    db: Session = Depends(get_db),
):
    """Run an end-to-end batch simulation on failed payments."""
    return SimulationRunner.run(
        db=db,
        seed=req.seed,
        limit=req.limit if not req.all_payments else None,
        all_payments=req.all_payments,
        mode=req.mode,
        fast_mode=req.fast_mode,
    )
