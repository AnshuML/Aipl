"""
Translation service with caching and error handling.
"""
import streamlit as st
from googletrans import Translator
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class TranslationService:
    """Service for handling text translation with caching"""
    
    def __init__(self):
        self.translator = Translator()
    
    # @st.cache_data(ttl=3600)  # Cache translations for 1 hour
    def translate_text(_self, text: str, target_language: str, source_language: str = 'auto') -> str:
        """
        Translate text to target language with caching.
        
        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'hi', 'ta')
            source_language: Source language code (default: 'auto')
            
        Returns:
            Translated text or original text if translation fails
        """
        if target_language == 'en' or not text.strip():
            return text
        
        try:
            result = _self.translator.translate(
                text, 
                dest=target_language, 
                src=source_language
            )
            return result.text
        except Exception as e:
            logger.warning(f"Translation failed for '{text[:50]}...': {e}")
            return text
    
    def detect_language(self, text: str) -> Optional[str]:
        """
        Detect language of given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code or None if detection fails
        """
        try:
            result = self.translator.detect(text)
            return result.lang
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return None
    
    def is_translation_needed(self, target_language: str) -> bool:
        """Check if translation is needed for target language"""
        return target_language != 'en'
    
    def get_supported_languages(self) -> dict:
        """Get supported language codes and names"""
        from googletrans import LANGUAGES
        return LANGUAGES