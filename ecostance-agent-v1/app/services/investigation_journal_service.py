import logging
from typing import Any, Dict
from app.db.database import SessionLocal
from app.models.investigation_journal import InvestigationJournal

logger = logging.getLogger(__name__)

def log_investigation_step(
    session_id: str,
    agent_type: str,
    tenant_id: str = None,
    thought: str = None,
    tool_name: str = None,
    tool_args: Dict[str, Any] = None,
    tool_result: str = None,
    step_number: int = 1
):
    """
    Persist a single step of an agent's investigation to the database.
    """
    try:
        db = SessionLocal()
        try:
            journal_entry = InvestigationJournal(
                tenant_id=tenant_id,
                session_id=session_id,
                agent_type=agent_type,
                step_number=step_number,
                thought=thought,
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=tool_result
            )
            db.add(journal_entry)
            db.commit()
            logger.info(f"Logged investigation step {step_number} for session {session_id}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to log investigation step: {e}")
