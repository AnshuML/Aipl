"""
Centralized configuration management
"""
import os
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Model configuration settings"""
    embedding_model: str = "sentence-transformers/all-mpnet-base-v2"
    llm_model: str = "gemini-1.5-flash"
    temperature: float = 0.3
    chunk_size: int = 1500
    chunk_overlap: int = 300


@dataclass
class UIConfig:
    """UI configuration settings"""
    page_title: str = "HR Mind"
    layout: str = "centered"
    page_icon: str = "💼"


@dataclass
class DirectoryConfig:
    """Directory paths configuration"""
    uploads_dir: str = "uploads"
    index_dir: str = "faiss_index"


class AppConfig:
    """Main application configuration"""
    
    _instance = None
    
    DEPARTMENTS: List[str] = [
        "HR", "Accounts", "Sales", "Marketing", 
        "IT", "Operations", "Customer Support"
    ]
    
    LANGUAGE_OPTIONS: Dict[str, str] = {
        'English': 'en',
        'Hindi (हिन्दी)': 'hi',
        'Tamil (தமிழ்)': 'ta',
        'Telugu (తెలుగు)': 'te',
        'Bengali (বাংলা)': 'bn',
        'Malayalam (മലയാളം)': 'ml',
        'Kannada (ಕನ್ನಡ)': 'kn',
        'Gujarati (ગુજરાતી)': 'gu',
        'Marathi (मराठी)': 'mr',
        'Urdu (اردو)': 'ur',
        'Odia (ଓଡ଼ିଆ)': 'or',
        'Assamese (অসমীয়া)': 'as',
        'Punjabi (ਪੰਜਾਬੀ)': 'pa',
        'Sindhi (سنधي)': 'sd',
        'Yoruba (Nigeria)': 'yo',
        'Igbo (Nigeria)': 'ig',
        'Hausa (Nigeria)': 'ha',
        'Sinhala (සිංහල)': 'si',
    }
    
    # Authentication
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if not hasattr(self, '_initialized'):
            self.model = ModelConfig()
            self.ui = UIConfig()
            self.directories = DirectoryConfig()
            
            # Load from environment if available
            self._load_from_env()
            self._initialized = True
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        self.model.llm_model = os.getenv("LLM_MODEL", self.model.llm_model)
        
        # Handle temperature with validation
        temp_str = os.getenv("LLM_TEMPERATURE")
        if temp_str is not None:
            try:
                self.model.temperature = float(temp_str)
            except ValueError:
                raise ValueError(f"Invalid temperature value: {temp_str}")
        else:
            self.model.temperature = self.model.temperature
            
        self.ui.page_title = os.getenv("APP_TITLE", self.ui.page_title)
    
    @classmethod
    def get_instance(cls):
        """Singleton pattern for configuration"""
        return cls()


# Global configuration instance
config = AppConfig.get_instance()