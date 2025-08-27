"""
Data models for query processing.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class QueryContext:
    """Context for query processing"""
    query: str
    department: str
    language: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def clean_query(self) -> str:
        """Get query without language tags"""
        import re
        return re.sub(r"\([^)]*\)|\[[^\]]*\]", "", self.query).strip()

@dataclass
class QueryResult:
    """Result of query processing"""
    response: str
    department: str
    language: str
    processing_time: float
    source_documents: Optional[List[Any]] = None
    confidence_score: Optional[float] = None
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        """Check if query was processed successfully"""
        return self.error is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'response': self.response,
            'department': self.department,
            'language': self.language,
            'processing_time': self.processing_time,
            'confidence_score': self.confidence_score,
            'error': self.error,
            'timestamp': datetime.now().isoformat()
        }

@dataclass
class ValidationResult:
    """Result of query validation"""
    is_valid: bool
    detected_department: Optional[str] = None
    confidence: float = 0.0
    message: Optional[str] = None