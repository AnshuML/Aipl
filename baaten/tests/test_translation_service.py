"""
Unit tests for TranslationService module
"""
import unittest
from unittest.mock import Mock, patch, MagicMock

# Import the module to test
from services.translation_service import TranslationService


class TestTranslationService(unittest.TestCase):
    """Test TranslationService class"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = TranslationService()
    
    @patch('services.translation_service.Translator')
    def test_initialization(self, mock_translator_class):
        """Test TranslationService initialization"""
        mock_translator = Mock()
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        self.assertIsNotNone(service.translator)
        mock_translator_class.assert_called_once()
    
    def test_translate_text_english_to_english(self):
        """Test translation from English to English (no translation needed)"""
        text = "Hello, how are you?"
        target_language = "en"
        
        result = self.service.translate_text(text, target_language)
        self.assertEqual(result, text)  # Should return original text
    
    def test_translate_text_empty_string(self):
        """Test translation of empty string"""
        text = ""
        target_language = "hi"
        
        result = self.service.translate_text(text, target_language)
        self.assertEqual(result, "")  # Should return empty string
    
    def test_translate_text_whitespace_only(self):
        """Test translation of whitespace-only string"""
        text = "   \n\t  "
        target_language = "hi"
        
        result = self.service.translate_text(text, target_language)
        self.assertEqual(result, text)  # Should return original text
    
    @patch('services.translation_service.Translator')
    def test_translate_text_success(self, mock_translator_class):
        """Test successful translation"""
        # Mock translator
        mock_translator = Mock()
        mock_result = Mock()
        mock_result.text = "नमस्ते, आप कैसे हैं?"
        mock_translator.translate.return_value = mock_result
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        text = "Hello, how are you?"
        target_language = "hi"
        
        result = service.translate_text(text, target_language)
        
        self.assertEqual(result, "नमस्ते, आप कैसे हैं?")
        mock_translator.translate.assert_called_once_with(
            text, dest=target_language, src='auto'
        )
    
    @patch('services.translation_service.Translator')
    def test_translate_text_with_source_language(self, mock_translator_class):
        """Test translation with specified source language"""
        # Mock translator
        mock_translator = Mock()
        mock_result = Mock()
        mock_result.text = "Hello, how are you?"
        mock_translator.translate.return_value = mock_result
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        text = "नमस्ते, आप कैसे हैं?"
        target_language = "en"
        source_language = "hi"
        
        result = service.translate_text(text, target_language, source_language)
        
        self.assertEqual(result, "Hello, how are you?")
        mock_translator.translate.assert_called_once_with(
            text, dest=target_language, src=source_language
        )
    
    @patch('services.translation_service.Translator')
    @patch('services.translation_service.logger')
    def test_translate_text_failure(self, mock_logger, mock_translator_class):
        """Test translation failure handling"""
        # Mock translator to raise exception
        mock_translator = Mock()
        mock_translator.translate.side_effect = Exception("Translation API error")
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        text = "Hello, how are you?"
        target_language = "hi"
        
        result = service.translate_text(text, target_language)
        
        # Should return original text on failure
        self.assertEqual(result, text)
        
        # Should log warning
        mock_logger.warning.assert_called_once()
        self.assertIn("Translation failed", mock_logger.warning.call_args[0][0])
    
    @patch('services.translation_service.Translator')
    def test_detect_language_success(self, mock_translator_class):
        """Test successful language detection"""
        # Mock translator
        mock_translator = Mock()
        mock_result = Mock()
        mock_result.lang = "hi"
        mock_translator.detect.return_value = mock_result
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        text = "नमस्ते, आप कैसे हैं?"
        
        result = service.detect_language(text)
        
        self.assertEqual(result, "hi")
        mock_translator.detect.assert_called_once_with(text)
    
    @patch('services.translation_service.Translator')
    @patch('services.translation_service.logger')
    def test_detect_language_failure(self, mock_logger, mock_translator_class):
        """Test language detection failure handling"""
        # Mock translator to raise exception
        mock_translator = Mock()
        mock_translator.detect.side_effect = Exception("Detection API error")
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        text = "Some text"
        
        result = service.detect_language(text)
        
        # Should return None on failure
        self.assertIsNone(result)
        
        # Should log warning
        mock_logger.warning.assert_called_once()
        self.assertIn("Language detection failed", mock_logger.warning.call_args[0][0])
    
    def test_is_translation_needed_english(self):
        """Test translation need check for English"""
        result = self.service.is_translation_needed("en")
        self.assertFalse(result)
    
    def test_is_translation_needed_non_english(self):
        """Test translation need check for non-English languages"""
        languages = ["hi", "ta", "te", "bn", "ml", "kn", "gu", "mr", "ur"]
        
        for lang in languages:
            result = self.service.is_translation_needed(lang)
            self.assertTrue(result, f"Should need translation for {lang}")
    
    def test_get_supported_languages(self):
        """Test getting supported languages"""
        with patch('services.translation_service.LANGUAGES', {'en': 'english', 'hi': 'hindi'}):
            result = self.service.get_supported_languages()
            
            self.assertIsInstance(result, dict)
            self.assertIn('en', result)
            self.assertIn('hi', result)
            self.assertEqual(result['en'], 'english')
            self.assertEqual(result['hi'], 'hindi')


class TestTranslationServiceIntegration(unittest.TestCase):
    """Integration tests for TranslationService"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = TranslationService()
    
    @patch('services.translation_service.Translator')
    def test_multiple_translations(self, mock_translator_class):
        """Test multiple consecutive translations"""
        # Mock translator
        mock_translator = Mock()
        
        # Mock different translation results
        def mock_translate_side_effect(text, dest, src):
            translations = {
                ("Hello", "hi"): "नमस्ते",
                ("Thank you", "hi"): "धन्यवाद",
                ("Good morning", "ta"): "காலை வணக்கம்"
            }
            mock_result = Mock()
            mock_result.text = translations.get((text, dest), text)
            return mock_result
        
        mock_translator.translate.side_effect = mock_translate_side_effect
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        # Test multiple translations
        result1 = service.translate_text("Hello", "hi")
        result2 = service.translate_text("Thank you", "hi")
        result3 = service.translate_text("Good morning", "ta")
        
        self.assertEqual(result1, "नमस्ते")
        self.assertEqual(result2, "धन्यवाद")
        self.assertEqual(result3, "காலை வணக்கம்")
        
        # Verify all calls were made
        self.assertEqual(mock_translator.translate.call_count, 3)
    
    @patch('services.translation_service.Translator')
    def test_long_text_translation(self, mock_translator_class):
        """Test translation of long text"""
        # Mock translator
        mock_translator = Mock()
        mock_result = Mock()
        mock_result.text = "लंबा अनुवादित पाठ..."
        mock_translator.translate.return_value = mock_result
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        # Long text
        long_text = "This is a very long text " * 100  # 500+ words
        
        result = service.translate_text(long_text, "hi")
        
        self.assertEqual(result, "लंबा अनुवादित पाठ...")
        mock_translator.translate.assert_called_once()
    
    @patch('services.translation_service.Translator')
    def test_special_characters_translation(self, mock_translator_class):
        """Test translation of text with special characters"""
        # Mock translator
        mock_translator = Mock()
        mock_result = Mock()
        mock_result.text = "विशेष वर्ण: @#$%"
        mock_translator.translate.return_value = mock_result
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        text_with_special_chars = "Special characters: @#$% & <html> tags"
        
        result = service.translate_text(text_with_special_chars, "hi")
        
        self.assertEqual(result, "विशेष वर्ण: @#$%")
        mock_translator.translate.assert_called_once()
    
    @patch('services.translation_service.Translator')
    def test_mixed_language_text(self, mock_translator_class):
        """Test translation of mixed language text"""
        # Mock translator
        mock_translator = Mock()
        mock_result = Mock()
        mock_result.text = "मिश्रित भाषा text"
        mock_translator.translate.return_value = mock_result
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        mixed_text = "Hello नमस्ते world दुनिया"
        
        result = service.translate_text(mixed_text, "hi")
        
        self.assertEqual(result, "मिश्रित भाषा text")
        mock_translator.translate.assert_called_once()


class TestTranslationServicePerformance(unittest.TestCase):
    """Performance tests for TranslationService"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = TranslationService()
    
    @patch('services.translation_service.Translator')
    def test_translation_performance(self, mock_translator_class):
        """Test translation performance with multiple requests"""
        # Mock translator
        mock_translator = Mock()
        mock_result = Mock()
        mock_result.text = "अनुवादित पाठ"
        mock_translator.translate.return_value = mock_result
        mock_translator_class.return_value = mock_translator
        
        service = TranslationService()
        
        import time
        
        # Test multiple translations
        start_time = time.time()
        
        for i in range(10):
            result = service.translate_text(f"Test text {i}", "hi")
            self.assertEqual(result, "अनुवादित पाठ")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(execution_time, 1.0, "Translation should be fast enough")
        
        # Verify all calls were made
        self.assertEqual(mock_translator.translate.call_count, 10)


if __name__ == '__main__':
    unittest.main()
