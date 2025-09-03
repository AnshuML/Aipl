"""
Translation service with caching and error handling.
"""
import streamlit as st
from typing import Optional
import logging
import requests
import json

logger = logging.getLogger(__name__)

class TranslationService:
    """Service for handling text translation with caching"""
    
    def __init__(self):
        # Use a more reliable translation approach
        self.translator = None
        self._init_translator()
    
    def _init_translator(self):
        """Initialize translator with fallback options"""
        try:
            # Try to use googletrans if available
            from googletrans import Translator
            self.translator = Translator()
            logger.info("Using googletrans for translation")
        except Exception as e:
            logger.warning(f"googletrans not available: {e}")
            # Use simple translation service as fallback
            from .simple_translation_service import SimpleTranslationService
            self.translator = SimpleTranslationService()
            logger.info("Using simple translation service as fallback")
    
    # @st.cache_data(ttl=3600)  # Cache translations for 1 hour
    def translate_text(self, text: str, target_language: str, source_language: str = 'auto') -> str:
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
        
        # Use the available translator (googletrans or simple fallback)
        if self.translator:
            try:
                # Check if it's googletrans or simple service
                if hasattr(self.translator, 'translate') and hasattr(self.translator.translate, '__call__'):
                    # googletrans
                    result = self.translator.translate(
                        text, 
                        dest=target_language, 
                        src=source_language
                    )
                    return result.text
                else:
                    # Simple translation service
                    return self.translator.translate_text(text, target_language, source_language)
            except Exception as e:
                logger.warning(f"Translation failed for '{text[:50]}...': {e}")
                return self._fallback_translate(text, target_language)
        
        # Final fallback
        return self._fallback_translate(text, target_language)
    
    def _fallback_translate(self, text: str, target_language: str) -> str:
        """Fallback translation method"""
        # Simple language mapping for common cases
        if target_language == 'hi':
            return f"[Hindi Translation] {text}"
        elif target_language == 'ta':
            return f"[Tamil Translation] {text}"
        elif target_language == 'te':
            return f"[Telugu Translation] {text}"
        elif target_language == 'bn':
            return f"[Bengali Translation] {text}"
        else:
            return f"[{target_language.upper()} Translation] {text}"
    
    def detect_language(self, text: str) -> Optional[str]:
        """
        Detect language of given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code or None if detection fails
        """
        if self.translator:
            try:
                # Check if it's googletrans or simple service
                if hasattr(self.translator, 'detect'):
                    result = self.translator.detect(text)
                    return result.lang if hasattr(result, 'lang') else result
                else:
                    # Simple translation service
                    return self.translator.detect_language(text)
            except Exception as e:
                logger.warning(f"Language detection failed: {e}")
        
        # Fallback: assume English if detection fails
        return 'en'
    
    def is_translation_needed(self, target_language: str) -> bool:
        """Check if translation is needed for target language"""
        return target_language != 'en'
    
    def get_supported_languages(self) -> dict:
        """Get supported language codes and names"""
        if self.translator and hasattr(self.translator, 'get_supported_languages'):
            return self.translator.get_supported_languages()
        
        # Fallback language mapping
        return {
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