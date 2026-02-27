from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, JSON
from app.db.database import Base

class InvestigationJournal(Base):
    """
    Model for storing the detailed investigation reasoning (thoughts) 
    of AI agents for SOC compliance and auditing.
    """
    
    __tablename__ = "investigation_journals"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=True)
    session_id = Column(String, index=True, nullable=False)
    agent_type = Column(String, index=True, nullable=False) # 'generic' or 'security_analyst'
    
    step_number = Column(Integer, default=1)
    thought = Column(Text, nullable=True)
    
    tool_name = Column(String, nullable=True)
    tool_args = Column(JSON, nullable=True)
    tool_result = Column(Text, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<InvestigationJournal(session={self.session_id}, step={self.step_number}, tool={self.tool_name})>"
