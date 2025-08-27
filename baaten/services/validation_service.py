"""
Query validation service with department matching.
"""
from typing import Tuple, List
import logging
from models.query_models import ValidationResult
from config.app_config import get_config

logger = logging.getLogger(__name__)

class QueryValidationService:
    """Service for validating queries against departments"""
    
    def __init__(self):
        self.config = get_config()
        self.department_keywords = self.config.departments.keywords
    
    def validate_department_query(self, query: str, selected_department: str) -> ValidationResult:
        """
        Validate if query matches selected department.
        
        Args:
            query: User query
            selected_department: Currently selected department
            
        Returns:
            ValidationResult with validation status and suggestions
        """
        query_lower = query.lower()
        
        # Check if query contains keywords from selected department
        selected_keywords = self.department_keywords.get(selected_department, [])
        query_matches_selected = any(keyword in query_lower for keyword in selected_keywords)
        
        if query_matches_selected:
            return ValidationResult(
                is_valid=True,
                confidence=self._calculate_confidence(query_lower, selected_keywords)
            )
        
        # Check if query matches other departments
        best_match = self._find_best_department_match(query_lower, selected_department)
        
        if best_match:
            return ValidationResult(
                is_valid=False,
                detected_department=best_match['department'],
                confidence=best_match['confidence'],
                message=self._get_mismatch_message(selected_department, best_match['department'])
            )
        
        # If no specific department keywords found, allow the query
        return ValidationResult(
            is_valid=True,
            confidence=0.5,
            message="Generic query - processing with selected department"
        )
    
    def _calculate_confidence(self, query: str, keywords: List[str]) -> float:
        """Calculate confidence score based on keyword matches"""
        matches = sum(1 for keyword in keywords if keyword in query)
        return min(matches / len(keywords), 1.0) if keywords else 0.0
    
    def _find_best_department_match(self, query: str, exclude_department: str) -> dict:
        """Find the best matching department for the query"""
        best_match = None
        best_score = 0
        
        for dept, keywords in self.department_keywords.items():
            if dept == exclude_department:
                continue
                
            score = self._calculate_confidence(query, keywords)
            if score > best_score and score > 0.3:  # Minimum confidence threshold
                best_score = score
                best_match = {'department': dept, 'confidence': score}
        
        return best_match
    
    def _get_mismatch_message(self, selected_dept: str, detected_dept: str) -> str:
        """Generate department mismatch message"""
        return (
            f"Query seems related to {detected_dept} department, "
            f"but {selected_dept} is selected. Consider switching departments."
        )
    
    def get_example_questions(self, department: str) -> List[str]:
        """Get example questions for a department"""
        examples = {
            'HR': [
                "What is the leave policy?",
                "How to apply for performance appraisal?",
                "What are employee benefits?"
            ],
            'Accounts': [
                "How to submit expense reports?",
                "What is the payment process?",
                "How to create invoices?"
            ],
            'Sales': [
                "What are sales targets?",
                "How to track leads?",
                "What is commission structure?"
            ],
            'Marketing': [
                "How to create campaigns?",
                "What are brand guidelines?",
                "How to measure ROI?"
            ],
            'IT': [
                "How to request software access?",
                "What are security policies?",
                "How to report technical issues?"
            ],
            'Operations': [
                "What are operational procedures?",
                "How to manage inventory?",
                "What are quality standards?"
            ],
            'Customer Support': [
                "How to handle complaints?",
                "What is ticket resolution process?",
                "How to escalate issues?"
            ]
        }
        return examples.get(department, ["Ask questions related to this department"])
    
    def is_product_query(self, query: str) -> bool:
        """Check if query is about products"""
        product_keywords = ['product', 'price', 'buy', 'cost', 'purchase', 'item']
        return any(word in query.lower() for word in product_keywords)