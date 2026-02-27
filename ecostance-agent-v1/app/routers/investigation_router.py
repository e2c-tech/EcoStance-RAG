from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.models.investigation_journal import InvestigationJournal
from pydantic import BaseModel

router = APIRouter()

class InvestigationStepResponse(BaseModel):
    id: int
    session_id: str
    agent_type: str
    step_number: int
    thought: Optional[str]
    tool_name: Optional[str]
    tool_args: Optional[dict]
    tool_result: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

@router.get("/journal/{session_id}", response_model=List[InvestigationStepResponse])
def get_investigation_journal(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve the step-by-step investigation journal for a specific session ID.
    Used for SOC compliance and audit reviews.
    """
    journal = db.query(InvestigationJournal)\
        .filter(InvestigationJournal.session_id == session_id)\
        .order_by(InvestigationJournal.step_number.asc())\
        .all()
    
    if not journal:
        raise HTTPException(status_code=404, detail="No investigation journal found for this session.")
        
    return journal

@router.get("/sessions", response_model=List[str])
def list_sessions_with_journals(
    db: Session = Depends(get_db)
):
    """List all unique session IDs that have investigation journals."""
    sessions = db.query(InvestigationJournal.session_id).distinct().all()
    return [s[0] for s in sessions]
