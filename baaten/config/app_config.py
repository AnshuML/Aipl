"""
Application configuration management with environment variable support.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ModelConfig:
    """LLM and embedding model configuration"""
    embedding_model: str = "sentence-transformers/all-mpnet-base-v2"
    llm_model: str = "gemini-1.5-flash"
    temperature: float = 0.3
    max_tokens: int = 1000

@dataclass
class DepartmentConfig:
    """Department-specific configuration"""
    departments: List[str] = field(default_factory=lambda: [
        "HR", "Accounts", "Sales", "Marketing", 
        "IT", "Operations", "Customer Support"
    ])
    
    keywords: Dict[str, List[str]] = field(default_factory=lambda: {
        'HR': ['policy', 'leave', 'employee', 'salary', 'benefits', 'recruitment'],
        'Accounts': ['invoice', 'payment', 'budget', 'expense', 'finance', 'accounting'],
        'Sales': ['sales', 'customer', 'lead', 'revenue', 'target', 'commission'],
        'Marketing': ['campaign', 'brand', 'promotion', 'advertising', 'social media'],
        'IT': ['software', 'hardware', 'network', 'security', 'database', 'server'],
        'Operations': ['process', 'workflow', 'operations', 'logistics', 'supply chain'],
        'Customer Support': ['support', 'ticket', 'complaint', 'service', 'help', 'issue']
    })

@dataclass
class LanguageConfig:
    """Language and translation configuration"""
    supported_languages: Dict[str, str] = field(default_factory=lambda: {
        'English': 'en',
        'Hindi (हिन्दी)': 'hi',
        'Tamil (தமிழ்)': 'ta',
        'Telugu (తెలుగు)': 'te',
        'Bengali (বাংলা)': 'bn',
        'Malayalam (മലയാളം)': 'ml',
        'Kannada (ಕನ್ನಡ)': 'kn',
        'Gujarati (ગુજરાતી)': 'gu',
        'Marathi (मराठी)': 'mr',
        'Urdu (اردو)': 'ur'
    })

@dataclass
class AppConfig:
    """Main application configuration"""
    google_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    
    # Sub-configurations
    model: ModelConfig = field(default_factory=ModelConfig)
    departments: DepartmentConfig = field(default_factory=DepartmentConfig)
    languages: LanguageConfig = field(default_factory=LanguageConfig)
    
    # UI Configuration
    page_title: str = "HR Mind"
    page_icon: str = "💼"
    layout: str = "centered"
    
    def __post_init__(self):
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")

# Singleton instance
_config_instance = None

def get_config() -> AppConfig:
    """Get singleton configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance