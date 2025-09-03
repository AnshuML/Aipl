"""
Unit tests for configuration modules
"""
import unittest
import os
from unittest.mock import patch, MagicMock
import tempfile
import shutil

# Import modules to test
from config import AppConfig, ModelConfig, UIConfig, DirectoryConfig


class TestModelConfig(unittest.TestCase):
    """Test ModelConfig class"""
    
    def test_default_values(self):
        """Test default configuration values"""
        config = ModelConfig()
        self.assertEqual(config.embedding_model, "sentence-transformers/all-mpnet-base-v2")
        self.assertEqual(config.llm_model, "gemini-1.5-flash")
        self.assertEqual(config.temperature, 0.3)
        self.assertEqual(config.chunk_size, 1500)
        self.assertEqual(config.chunk_overlap, 300)
    
    def test_custom_values(self):
        """Test custom configuration values"""
        config = ModelConfig(
            embedding_model="custom-model",
            llm_model="gpt-4",
            temperature=0.5,
            chunk_size=2000,
            chunk_overlap=400
        )
        self.assertEqual(config.embedding_model, "custom-model")
        self.assertEqual(config.llm_model, "gpt-4")
        self.assertEqual(config.temperature, 0.5)
        self.assertEqual(config.chunk_size, 2000)
        self.assertEqual(config.chunk_overlap, 400)


class TestUIConfig(unittest.TestCase):
    """Test UIConfig class"""
    
    def test_default_values(self):
        """Test default UI configuration"""
        config = UIConfig()
        self.assertEqual(config.page_title, "HR Mind")
        self.assertEqual(config.layout, "centered")
        self.assertEqual(config.page_icon, "💼")


class TestDirectoryConfig(unittest.TestCase):
    """Test DirectoryConfig class"""
    
    def test_default_values(self):
        """Test default directory configuration"""
        config = DirectoryConfig()
        self.assertEqual(config.uploads_dir, "uploads")
        self.assertEqual(config.index_dir, "faiss_index")


class TestAppConfig(unittest.TestCase):
    """Test AppConfig class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_departments_list(self):
        """Test departments configuration"""
        config = AppConfig()
        expected_departments = [
            "HR", "Accounts", "Sales", "Marketing", 
            "IT", "Operations", "Customer Support"
        ]
        self.assertEqual(config.DEPARTMENTS, expected_departments)
    
    def test_language_options(self):
        """Test language configuration"""
        config = AppConfig()
        self.assertIn('English', config.LANGUAGE_OPTIONS)
        self.assertIn('Hindi (हिन्दी)', config.LANGUAGE_OPTIONS)
        self.assertEqual(config.LANGUAGE_OPTIONS['English'], 'en')
        self.assertEqual(config.LANGUAGE_OPTIONS['Hindi (हिन्दी)'], 'hi')
    
    def test_admin_credentials(self):
        """Test admin credentials"""
        config = AppConfig()
        self.assertEqual(config.ADMIN_USERNAME, "admin")
        self.assertEqual(config.ADMIN_PASSWORD, "admin123")
    
    def test_config_initialization(self):
        """Test configuration initialization"""
        config = AppConfig()
        self.assertIsInstance(config.model, ModelConfig)
        self.assertIsInstance(config.ui, UIConfig)
        self.assertIsInstance(config.directories, DirectoryConfig)
    
    @patch.dict(os.environ, {
        'LLM_MODEL': 'gpt-4',
        'LLM_TEMPERATURE': '0.5',
        'APP_TITLE': 'Test App'
    })
    def test_load_from_env(self):
        """Test loading configuration from environment variables"""
        # Reset singleton for this test
        AppConfig._instance = None
        config = AppConfig()
        self.assertEqual(config.model.llm_model, 'gpt-4')
        self.assertEqual(config.model.temperature, 0.5)
        self.assertEqual(config.ui.page_title, 'Test App')
    
    def test_singleton_pattern(self):
        """Test singleton pattern implementation"""
        config1 = AppConfig.get_instance()
        config2 = AppConfig.get_instance()
        self.assertIs(config1, config2)
    
    def test_invalid_temperature(self):
        """Test invalid temperature value handling"""
        with patch.dict(os.environ, {'LLM_TEMPERATURE': 'invalid'}):
            # Reset singleton for this test
            AppConfig._instance = None
            with self.assertRaises(ValueError):
                AppConfig()


if __name__ == '__main__':
    unittest.main()
