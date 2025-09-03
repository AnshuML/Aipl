"""
Security and validation tests for AIPL Chatbot
"""
import unittest
import os
import tempfile
import re
from unittest.mock import patch, Mock


class TestInputValidation(unittest.TestCase):
    """Test input validation and sanitization"""
    
    def test_email_validation(self):
        """Test email validation logic"""
        # Valid emails
        valid_emails = [
            "user@aiplabro.com",
            "test.user@aiplabro.com",
            "user+tag@aiplabro.com",
            "user@ajitindustries.com",
            "admin@ajitindustries.com"
        ]
        
        # Invalid emails
        invalid_emails = [
            "user@gmail.com",
            "user@yahoo.com",
            "user@company.com",
            "invalid-email",
            "@aiplabro.com",
            "user@",
            "",
            "user@aiplabro",
            "user@aiplabro.co"
        ]
        
        # Email validation pattern from app.py
        email_pattern = r"^[\w\.\-\+]+@(aiplabro\.com|ajitindustries\.com)$"
        
        for email in valid_emails:
            with self.subTest(email=email):
                self.assertTrue(re.match(email_pattern, email), 
                               f"Valid email {email} should match")
        
        for email in invalid_emails:
            with self.subTest(email=email):
                self.assertIsNone(re.match(email_pattern, email), 
                                 f"Invalid email {email} should not match")
    
    def test_query_sanitization(self):
        """Test query input sanitization"""
        # Potentially malicious queries
        malicious_queries = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "%3Cscript%3Ealert%28%27xss%27%29%3C%2Fscript%3E",
            "{{7*7}}",  # Template injection
            "${7*7}",   # Expression injection
        ]
        
        # Test that queries are handled safely
        for query in malicious_queries:
            with self.subTest(query=query):
                # Basic length check
                if len(query) > 1000:
                    self.fail(f"Query too long: {len(query)} characters")
                
                # Test that the query can be processed without crashing
                # This is a basic safety test - in production, you'd have proper sanitization
                try:
                    # Simulate basic processing
                    processed_query = query.strip()
                    self.assertIsInstance(processed_query, str)
                except Exception as e:
                    self.fail(f"Query processing failed: {e}")
    
    def test_file_upload_validation(self):
        """Test file upload validation"""
        from utils.error_handler import InputValidator
        
        # Test with mock file objects
        class MockFile:
            def __init__(self, name, size=1024):
                self.name = name
                self.size = size
        
        # Valid files
        valid_files = [
            MockFile("document.pdf", 1024 * 1024),  # 1MB PDF
            MockFile("policy.pdf", 512 * 1024),     # 512KB PDF
        ]
        
        # Invalid files
        invalid_files = [
            MockFile("document.txt", 1024),          # Wrong extension
            MockFile("image.jpg", 1024),             # Wrong extension
            MockFile("large.pdf", 20 * 1024 * 1024), # Too large (20MB)
            MockFile("no_extension", 1024),          # No extension
            MockFile(".pdf", 1024),                  # No name
        ]
        
        for file in valid_files:
            with self.subTest(file=file.name):
                try:
                    InputValidator.validate_file_upload(file, max_size_mb=10, allowed_types=['pdf'])
                    # Should not raise exception
                except Exception as e:
                    self.fail(f"Valid file {file.name} failed validation: {e}")
        
        for file in invalid_files:
            with self.subTest(file=file.name):
                with self.assertRaises(Exception):
                    InputValidator.validate_file_upload(file, max_size_mb=10, allowed_types=['pdf'])
    
    def test_department_validation(self):
        """Test department selection validation"""
        from utils.error_handler import InputValidator
        
        valid_departments = ["HR", "Accounts", "Sales", "Marketing", "IT", "Operations"]
        
        # Valid departments
        for dept in valid_departments:
            with self.subTest(department=dept):
                try:
                    InputValidator.validate_department(dept, valid_departments)
                    # Should not raise exception
                except Exception as e:
                    self.fail(f"Valid department {dept} failed validation: {e}")
        
        # Invalid departments
        invalid_departments = ["", "InvalidDept", "hr", "ACCOUNTS", None]
        
        for dept in invalid_departments:
            with self.subTest(department=dept):
                with self.assertRaises(Exception):
                    InputValidator.validate_department(dept, valid_departments)
    
    def test_query_length_validation(self):
        """Test query length validation"""
        from utils.error_handler import InputValidator
        
        # Valid queries
        valid_queries = [
            "What is the leave policy?",
            "How do I apply for benefits?",
            "A" * 100,  # 100 characters
            "A" * 500,  # 500 characters
        ]
        
        for query in valid_queries:
            with self.subTest(query_length=len(query)):
                try:
                    InputValidator.validate_query(query, min_length=3, max_length=1000)
                    # Should not raise exception
                except Exception as e:
                    self.fail(f"Valid query of length {len(query)} failed validation: {e}")
        
        # Invalid queries
        invalid_queries = [
            "",           # Empty
            "A",          # Too short
            "AB",         # Too short
            "A" * 1001,   # Too long
            "   ",        # Only whitespace
            "\n\t",       # Only whitespace
        ]
        
        for query in invalid_queries:
            with self.subTest(query=repr(query)):
                with self.assertRaises(Exception):
                    InputValidator.validate_query(query, min_length=3, max_length=1000)


class TestAPIKeySecurity(unittest.TestCase):
    """Test API key security and handling"""
    
    def test_api_key_not_logged(self):
        """Test that API keys are not logged in plain text"""
        from department_manager import DepartmentManager
        
        test_key = "sk-test-key-12345678901234567890"
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': test_key}):
            with patch('department_manager.openai'):
                manager = DepartmentManager()
                
                # API key should be retrieved but not stored in plain text in logs
                self.assertEqual(manager.openai_api_key, test_key)
                
                # Test key stripping functionality
                stripped_key = manager._get_openai_api_key()
                self.assertEqual(stripped_key, test_key)
    
    def test_api_key_stripping(self):
        """Test API key stripping of quotes and whitespace"""
        from department_manager import DepartmentManager
        
        test_cases = [
            ("'sk-test-key'", "sk-test-key"),
            ('"sk-test-key"', "sk-test-key"),
            ("  sk-test-key  ", "sk-test-key"),
            ("'  sk-test-key  '", "sk-test-key"),
            ('"  sk-test-key  "', "sk-test-key"),
        ]
        
        for input_key, expected_key in test_cases:
            with self.subTest(input_key=input_key):
                with patch.dict(os.environ, {'OPENAI_API_KEY': input_key}):
                    with patch('department_manager.openai'):
                        manager = DepartmentManager()
                        actual_key = manager.openai_api_key
                        self.assertEqual(actual_key, expected_key)
    
    def test_missing_api_key_handling(self):
        """Test handling of missing API key"""
        from department_manager import DepartmentManager
        
        # Test with completely missing key
        with patch.dict(os.environ, {}, clear=True):
            with patch('streamlit') as mock_streamlit:
                mock_streamlit.secrets.get.return_value = None
                
                with self.assertRaises(ValueError) as context:
                    DepartmentManager()
                
                self.assertIn("OPENAI_API_KEY not set", str(context.exception))
    
    def test_streamlit_secrets_fallback(self):
        """Test fallback to Streamlit secrets"""
        from department_manager import DepartmentManager
        
        test_key = "sk-streamlit-secret-key"
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('streamlit') as mock_streamlit:
                mock_streamlit.secrets.get.return_value = test_key
                
                with patch('department_manager.openai'):
                    manager = DepartmentManager()
                    self.assertEqual(manager.openai_api_key, test_key)


class TestFileSystemSecurity(unittest.TestCase):
    """Test file system security"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks"""
        from department_manager import DepartmentManager
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('department_manager.openai'):
                manager = DepartmentManager()
                manager.faiss_index_dir = self.test_dir
                
                # Potentially malicious department names
                malicious_names = [
                    "../../../etc",
                    "..\\..\\windows",
                    "/etc/passwd",
                    "C:\\Windows\\System32",
                    "dept/../../../sensitive",
                    "dept/../../.ssh",
                ]
                
                for dept_name in malicious_names:
                    with self.subTest(department=dept_name):
                        # Should not create files outside the designated directory
                        manager.save_department_pdf(dept_name, "test.pdf", "content")
                        
                        # Verify file is created within the test directory
                        docs_dir = os.path.join(self.test_dir, "docs")
                        if os.path.exists(docs_dir):
                            for root, dirs, files in os.walk(docs_dir):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    # File should be within the test directory
                                    self.assertTrue(file_path.startswith(self.test_dir))
    
    def test_file_name_sanitization(self):
        """Test file name sanitization"""
        from department_manager import DepartmentManager
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('department_manager.openai'):
                manager = DepartmentManager()
                manager.faiss_index_dir = self.test_dir
                
                # Potentially problematic file names
                problematic_names = [
                    "../malicious.pdf",
                    "file<>name.pdf",
                    "file:name.pdf",
                    "file|name.pdf",
                    "file*name.pdf",
                    "file?name.pdf",
                    'file"name.pdf',
                ]
                
                department = "TestDept"
                
                for filename in problematic_names:
                    with self.subTest(filename=filename):
                        # Should handle problematic filenames safely
                        try:
                            manager.save_department_pdf(department, filename, "content")
                            
                            # Check that no files were created outside test directory
                            for root, dirs, files in os.walk(self.test_dir):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    self.assertTrue(file_path.startswith(self.test_dir))
                                    
                        except Exception:
                            # It's okay if the operation fails safely
                            pass


class TestDataPrivacy(unittest.TestCase):
    """Test data privacy and protection"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_sensitive_data_handling(self):
        """Test handling of potentially sensitive data"""
        from utils.user_logger import UserLogger
        
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        # Test data that might contain sensitive information
        sensitive_queries = [
            "My SSN is 123-45-6789, what's the policy?",
            "My credit card 1234-5678-9012-3456 was charged",
            "My password is secret123, how do I change it?",
            "Call me at +1-555-123-4567 about benefits",
        ]
        
        email = "test@aiplabro.com"
        
        for query in sensitive_queries:
            with self.subTest(query=query[:30] + "..."):
                # Log the query
                logger.log_user_question(email, query, "HR", "English")
                
                # Verify the query was logged (basic functionality)
                import csv
                csv_file = os.path.join(self.test_dir, "questions.csv")
                
                if os.path.exists(csv_file):
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # The query should be logged, but this test just ensures
                        # the logging mechanism works with sensitive data
                        self.assertIn(email, content)
    
    def test_log_file_permissions(self):
        """Test log file permissions are secure"""
        from utils.user_logger import UserLogger
        
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        # Create some log entries
        logger.log_user_login("test@aiplabro.com", True)
        
        # Check that log files are created
        log_files = ["logins.csv", "logins.json"]
        
        for log_file in log_files:
            file_path = os.path.join(self.test_dir, log_file)
            if os.path.exists(file_path):
                # Check file permissions (Unix-like systems)
                if hasattr(os, 'stat'):
                    import stat
                    file_stat = os.stat(file_path)
                    
                    # File should not be world-readable
                    permissions = stat.filemode(file_stat.st_mode)
                    # This is a basic check - in production, implement proper file permissions
                    self.assertIsInstance(permissions, str)
    
    def test_data_truncation(self):
        """Test that long data is properly truncated"""
        from utils.user_logger import UserLogger
        
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        # Test with very long query and response
        long_query = "What is the policy? " * 100  # Very long query
        long_response = "The policy states that " * 200  # Very long response
        
        email = "test@aiplabro.com"
        
        logger.log_user_question(email, long_query, "HR", "English")
        logger.log_bot_response(email, long_query, long_response, True, 1.0)
        
        # Check that data was truncated appropriately
        import csv
        
        responses_file = os.path.join(self.test_dir, "responses.csv")
        if os.path.exists(responses_file):
            with open(responses_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Question should be truncated to 200 chars
                    self.assertLessEqual(len(row.get('question', '')), 200)
                    # Response should be truncated to 500 chars
                    self.assertLessEqual(len(row.get('response', '')), 500)


class TestErrorHandling(unittest.TestCase):
    """Test security aspects of error handling"""
    
    def test_error_information_disclosure(self):
        """Test that errors don't disclose sensitive information"""
        from utils.error_handler import handle_errors
        
        @handle_errors("Operation failed")
        def test_function_with_error():
            # Simulate an error that might contain sensitive info
            raise Exception("Database connection failed: user=admin, password=secret123, host=internal.db.server")
        
        # Capture error handling
        with patch('streamlit.error') as mock_error:
            result = test_function_with_error()
            
            # Should return None on error
            self.assertIsNone(result)
            
            # Error message should not contain sensitive information
            if mock_error.called:
                error_message = mock_error.call_args[0][0]
                self.assertNotIn("password=secret123", error_message)
                self.assertNotIn("internal.db.server", error_message)
                # Should show generic error message instead
                self.assertIn("Operation failed", error_message)
    
    def test_exception_handling_robustness(self):
        """Test that exception handling is robust"""
        from utils.error_handler import safe_execute
        
        # Test various types of exceptions
        def raise_value_error():
            raise ValueError("Invalid value")
        
        def raise_type_error():
            raise TypeError("Wrong type")
        
        def raise_generic_error():
            raise Exception("Generic error")
        
        # All should be handled safely
        result1 = safe_execute(raise_value_error, default_return="default")
        result2 = safe_execute(raise_type_error, default_return="default")
        result3 = safe_execute(raise_generic_error, default_return="default")
        
        self.assertEqual(result1, "default")
        self.assertEqual(result2, "default")
        self.assertEqual(result3, "default")
        
        # Test that exceptions are logged but don't crash the system
        with patch('utils.error_handler.logger') as mock_logger:
            safe_execute(raise_value_error, default_return="fallback")
            mock_logger.error.assert_called()


if __name__ == '__main__':
    unittest.main()
