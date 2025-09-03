"""
Simple translation service without external dependencies.
Provides fallback translation functionality for Streamlit Cloud deployment.
"""
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class SimpleTranslationService:
    """Simple translation service with basic language support"""
    
    def __init__(self):
        self.language_names = {
            'en': 'English',
            'hi': 'Hindi',
            'ta': 'Tamil',
            'te': 'Telugu',
            'bn': 'Bengali',
            'ml': 'Malayalam',
            'kn': 'Kannada',
            'gu': 'Gujarati',
            'mr': 'Marathi',
            'ur': 'Urdu',
            'or': 'Odia',
            'as': 'Assamese',
            'pa': 'Punjabi',
            'yo': 'Yoruba',
            'ig': 'Igbo',
            'ha': 'Hausa',
            'si': 'Sinhala'
        }
    
    def translate_text(self, text: str, target_language: str, source_language: str = 'auto') -> str:
        """
        Simple translation with language indicators.
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (ignored)
            
        Returns:
            Text with language indicator
        """
        if target_language == 'en' or not text.strip():
            return text
        
        language_name = self.language_names.get(target_language, target_language.upper())
        return f"[{language_name}] {text}"
    
    def detect_language(self, text: str) -> Optional[str]:
        """Simple language detection - assumes English"""
        return 'en'
    
    def is_translation_needed(self, target_language: str) -> bool:
        """Check if translation is needed"""
        return target_language != 'en'
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages"""
        return self.language_names.copy()
