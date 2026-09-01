"""API routes for AI Agent recovery execution."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.orchestrator import AgentOrchestrator
from app.agent.schemas import AgentRunResult
from app.core.database import get_db

router = APIRouter()


@router.post("/recover/{case_id}", response_model=AgentRunResult)
def run_recovery_agent(case_id: int, db: Session = Depends(get_db)):
    """Run the bounded AI Recovery Agent for a specific recovery case."""
    orchestrator = AgentOrchestrator()
    result = orchestrator.run(db, case_id)
    if result.final_state.value == "ERROR":
        raise HTTPException(status_code=404, detail=result.error)
    return result
