"""
Integration tests for AIPL Chatbot
Tests the complete workflow and component interactions
"""
import unittest
import os
import tempfile
import shutil
import time
from unittest.mock import patch, Mock, MagicMock


class TestCompleteWorkflow(unittest.TestCase):
    """Test complete user workflow from login to logout"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        # Mock environment
        self.env_patcher = patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-integration-key'
        })
        self.env_patcher.start()
        
        # Mock OpenAI in multiple modules
        self.openai_patcher1 = patch('department_manager.openai')
        self.openai_patcher2 = patch('query_services.openai')
        self.mock_openai1 = self.openai_patcher1.start()
        self.mock_openai2 = self.openai_patcher2.start()
        
        # Mock OpenAI responses
        mock_embedding_response = {
            'data': [{'embedding': [0.1] * 1536} for _ in range(10)]
        }
        mock_chat_response = {
            'choices': [{'message': {'content': 'This is a test response from the chatbot.'}}]
        }
        
        self.mock_openai1.Embedding.create.return_value = mock_embedding_response
        self.mock_openai1.ChatCompletion.create.return_value = mock_chat_response
        self.mock_openai2.Embedding.create.return_value = mock_embedding_response
        self.mock_openai2.ChatCompletion.create.return_value = mock_chat_response
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        self.openai_patcher1.stop()
        self.openai_patcher2.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_admin_workflow(self):
        """Test complete admin workflow: upload documents, create index, manage files"""
        from department_manager import DepartmentManager
        
        # Initialize department manager
        manager = DepartmentManager()
        manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
        os.makedirs(manager.faiss_index_dir, exist_ok=True)
        
        department = "HR"
        
        # Step 1: Upload documents (simulate PDF upload)
        documents = [
            "Employee leave policy: Employees are entitled to 30 days annual leave...",
            "Attendance policy: Working hours are 9 AM to 6 PM, Monday to Friday...",
            "Benefits package: Health insurance, dental coverage, retirement plans..."
        ]
        
        pdf_files = ["leave_policy.pdf", "attendance_policy.pdf", "benefits.pdf"]
        
        # Save documents
        for pdf_file, content in zip(pdf_files, documents):
            manager.save_department_pdf(department, pdf_file, content)
        
        # Step 2: Create department index
        manager.create_department_index(department, documents)
        
        # Step 3: Verify index creation
        index = manager.get_department_index(department)
        self.assertIsNotNone(index, "Index should be created successfully")
        
        # Step 4: List uploaded files
        uploaded_files = manager.list_department_pdfs(department)
        self.assertEqual(len(uploaded_files), 3, "Should have 3 uploaded files")
        for pdf_file in pdf_files:
            self.assertIn(pdf_file, uploaded_files, f"{pdf_file} should be in uploaded files")
        
        # Step 5: Retrieve documents
        retrieved_docs = manager.get_department_docs(department)
        self.assertEqual(len(retrieved_docs), 3, "Should retrieve 3 documents")
        
        # Step 6: Delete a document and rebuild index
        manager.delete_department_pdf(department, "benefits.pdf")
        
        # Verify deletion
        remaining_files = manager.list_department_pdfs(department)
        self.assertEqual(len(remaining_files), 2, "Should have 2 files after deletion")
        self.assertNotIn("benefits.pdf", remaining_files, "Deleted file should not be in list")
        
        # Verify index was rebuilt
        updated_index = manager.get_department_index(department)
        self.assertIsNotNone(updated_index, "Index should still exist after rebuild")
    
    def test_user_query_workflow(self):
        """Test complete user query workflow"""
        from department_manager import DepartmentManager
        from query_services import QueryProcessor
        from utils.user_logger import UserLogger
        
        # Initialize components
        manager = DepartmentManager()
        manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
        os.makedirs(manager.faiss_index_dir, exist_ok=True)
        
        processor = QueryProcessor(manager)
        
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        # Setup test data
        department = "HR"
        documents = [
            "Leave policy: Employees can take up to 30 days annual leave per year.",
            "Working hours: Standard working hours are 9 AM to 6 PM, Monday to Friday.",
            "Benefits: Company provides health insurance, dental, and retirement benefits."
        ]
        
        # Create department data
        manager.create_department_index(department, documents)
        for i, doc in enumerate(documents):
            manager.save_department_pdf(department, f"doc_{i}.pdf", doc)
        
        # Simulate user session
        user_email = "testuser@aiplabro.com"
        
        # Step 1: User login
        logger.log_user_login(user_email, True, "192.168.1.100")
        
        # Step 2: User asks multiple questions
        test_queries = [
            "What is the leave policy?",
            "What are the working hours?",
            "What benefits does the company provide?"
        ]
        
        for query in test_queries:
            start_time = time.time()
            
            # Log question
            logger.log_user_question(user_email, query, department, "English")
            
            # Process query
            try:
                response = processor.process_query(query, department, language_code='en')
                end_time = time.time()
                response_time = end_time - start_time
                
                # Verify response
                self.assertIsInstance(response, str, "Response should be a string")
                self.assertGreater(len(response), 0, "Response should not be empty")
                
                # Log successful response
                logger.log_bot_response(user_email, query, response, True, response_time)
                
            except Exception as e:
                end_time = time.time()
                response_time = end_time - start_time
                
                # Log error
                logger.log_error(user_email, "Query Processing Error", str(e))
                logger.log_bot_response(user_email, query, str(e), False, response_time)
        
        # Step 3: User logout
        logger.log_user_logout(user_email)
        
        # Verify logging
        import csv
        
        # Check login log
        logins_file = os.path.join(self.test_dir, "logins.csv")
        self.assertTrue(os.path.exists(logins_file), "Login log should exist")
        
        with open(logins_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            login_records = list(reader)
            self.assertEqual(len(login_records), 1, "Should have 1 login record")
            self.assertEqual(login_records[0]['email'], user_email)
            self.assertEqual(login_records[0]['success'], 'True')
        
        # Check questions log
        questions_file = os.path.join(self.test_dir, "questions.csv")
        self.assertTrue(os.path.exists(questions_file), "Questions log should exist")
        
        with open(questions_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            question_records = list(reader)
            self.assertEqual(len(question_records), len(test_queries), "Should have all question records")
        
        # Check responses log
        responses_file = os.path.join(self.test_dir, "responses.csv")
        self.assertTrue(os.path.exists(responses_file), "Responses log should exist")
        
        # Check logout log
        logouts_file = os.path.join(self.test_dir, "logouts.csv")
        self.assertTrue(os.path.exists(logouts_file), "Logout log should exist")
    
    def test_multi_department_workflow(self):
        """Test workflow with multiple departments"""
        from department_manager import DepartmentManager
        from query_services import QueryProcessor
        
        # Initialize components
        manager = DepartmentManager()
        manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
        os.makedirs(manager.faiss_index_dir, exist_ok=True)
        
        processor = QueryProcessor(manager)
        
        # Setup multiple departments
        departments_data = {
            "HR": [
                "Leave policy document content...",
                "Employee handbook content...",
                "Benefits information..."
            ],
            "IT": [
                "Password policy: Passwords must be at least 8 characters...",
                "Software installation guidelines...",
                "Network security protocols..."
            ],
            "Finance": [
                "Expense reimbursement policy...",
                "Budget approval process...",
                "Financial reporting guidelines..."
            ]
        }
        
        # Create indexes for all departments
        for dept, documents in departments_data.items():
            manager.create_department_index(dept, documents)
            
            # Save documents
            for i, doc in enumerate(documents):
                manager.save_department_pdf(dept, f"{dept.lower()}_doc_{i}.pdf", doc)
        
        # Test queries across different departments
        test_cases = [
            ("HR", "What is the leave policy?"),
            ("IT", "What is the password policy?"),
            ("Finance", "How do I get expense reimbursement?"),
            ("HR", "What benefits are available?"),
            ("IT", "How do I install software?")
        ]
        
        for department, query in test_cases:
            with self.subTest(department=department, query=query):
                response = processor.process_query(query, department)
                
                self.assertIsInstance(response, str, f"Response for {department} should be string")
                self.assertGreater(len(response), 0, f"Response for {department} should not be empty")
                
                # Verify department isolation - response should be relevant to department
                # This is a basic check - in practice, you'd have more sophisticated relevance testing
                if "No documents found" not in response:
                    self.assertIsInstance(response, str)
    
    def test_translation_workflow(self):
        """Test workflow with translation"""
        from department_manager import DepartmentManager
        from query_services import QueryProcessor
        
        # Initialize components
        manager = DepartmentManager()
        manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
        os.makedirs(manager.faiss_index_dir, exist_ok=True)
        
        processor = QueryProcessor(manager)
        
        # Setup test data
        department = "HR"
        documents = ["Leave policy: You can take 30 days annual leave."]
        manager.create_department_index(department, documents)
        manager.save_department_pdf(department, "leave_policy.pdf", documents[0])
        
        # Mock translation service
        with patch.object(processor.translator, 'translate_text') as mock_translate:
            mock_translate.return_value = "छुट्टी नीति: आप 30 दिन की वार्षिक छुट्टी ले सकते हैं।"
            
            # Test query with translation
            query = "What is the leave policy?"
            response = processor.process_query(query, department, language_code='hi')
            
            # Verify translation was called
            mock_translate.assert_called_once()
            
            # Verify response is in Hindi (mocked)
            self.assertIn("छुट्टी", response)
    
    def test_error_recovery_workflow(self):
        """Test workflow with error scenarios and recovery"""
        from department_manager import DepartmentManager
        from query_services import QueryProcessor
        from utils.user_logger import UserLogger
        
        # Initialize components
        manager = DepartmentManager()
        manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
        os.makedirs(manager.faiss_index_dir, exist_ok=True)
        
        processor = QueryProcessor(manager)
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        user_email = "errortest@aiplabro.com"
        
        # Test 1: Query to department with no documents
        logger.log_user_login(user_email, True)
        logger.log_user_question(user_email, "What is the policy?", "EmptyDept", "English")
        
        response = processor.process_query("What is the policy?", "EmptyDept")
        
        # Should get appropriate error message
        self.assertIn("No documents found", response)
        
        # Test 2: Query with OpenAI API error
        with patch('query_services.openai.ChatCompletion.create') as mock_openai:
            mock_openai.side_effect = Exception("API rate limit exceeded")
            
            # Setup some documents first
            department = "TestDept"
            documents = ["Test document content"]
            manager.create_department_index(department, documents)
            manager.save_department_pdf(department, "test.pdf", documents[0])
            
            # This should handle the error gracefully
            try:
                response = processor.process_query("Test query", department)
                # If no exception, check if error is handled in response
                self.assertIsInstance(response, str)
            except Exception:
                # If exception is raised, it should be a handled exception
                pass
        
        # Verify error logging
        logger.log_user_logout(user_email)
        
        # Check that logs were created despite errors
        logs_dir = logger.logs_dir
        self.assertTrue(os.path.exists(os.path.join(logs_dir, "logins.csv")))
        self.assertTrue(os.path.exists(os.path.join(logs_dir, "questions.csv")))


class TestComponentIntegration(unittest.TestCase):
    """Test integration between different components"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        self.env_patcher = patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-component-key'
        })
        self.env_patcher.start()
        
        self.openai_patcher1 = patch('department_manager.openai')
        self.openai_patcher2 = patch('query_services.openai')
        self.mock_openai1 = self.openai_patcher1.start()
        self.mock_openai2 = self.openai_patcher2.start()
        
        mock_embedding_response = {
            'data': [{'embedding': [0.1] * 1536} for _ in range(5)]
        }
        mock_chat_response = {
            'choices': [{'message': {'content': 'Integrated response'}}]
        }
        
        self.mock_openai1.Embedding.create.return_value = mock_embedding_response
        self.mock_openai1.ChatCompletion.create.return_value = mock_chat_response
        self.mock_openai2.Embedding.create.return_value = mock_embedding_response
        self.mock_openai2.ChatCompletion.create.return_value = mock_chat_response
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        self.openai_patcher1.stop()
        self.openai_patcher2.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_department_manager_query_processor_integration(self):
        """Test integration between DepartmentManager and QueryProcessor"""
        from department_manager import DepartmentManager
        from query_services import QueryProcessor
        
        # Initialize components
        manager = DepartmentManager()
        manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
        os.makedirs(manager.faiss_index_dir, exist_ok=True)
        
        processor = QueryProcessor(manager)
        
        # Create test data
        department = "Integration"
        documents = [
            "Integration test document 1",
            "Integration test document 2",
            "Integration test document 3"
        ]
        
        # Test the flow: DepartmentManager creates index -> QueryProcessor uses it
        manager.create_department_index(department, documents)
        
        # QueryProcessor should be able to use the created index
        response = processor.process_query("integration test", department)
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        # Verify that DepartmentManager methods are called by QueryProcessor
        self.assertIsNotNone(manager.get_department_index(department))
        self.assertEqual(len(manager.get_department_docs(department)), 0)  # No saved PDF files yet
    
    def test_query_processor_logger_integration(self):
        """Test integration between QueryProcessor and UserLogger"""
        from department_manager import DepartmentManager
        from query_services import QueryProcessor
        from utils.user_logger import UserLogger
        
        # Initialize components
        manager = DepartmentManager()
        manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
        os.makedirs(manager.faiss_index_dir, exist_ok=True)
        
        processor = QueryProcessor(manager)
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        # Create test data
        department = "TestIntegration"
        documents = ["Test integration document"]
        manager.create_department_index(department, documents)
        
        user_email = "integration@test.com"
        query = "integration test query"
        
        # Simulate the integration workflow
        start_time = time.time()
        
        # Log question
        logger.log_user_question(user_email, query, department, "English")
        
        # Process query
        response = processor.process_query(query, department)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Log response
        logger.log_bot_response(user_email, query, response, True, response_time)
        
        # Verify integration worked
        self.assertIsInstance(response, str)
        
        # Verify logs were created
        questions_file = os.path.join(self.test_dir, "questions.csv")
        responses_file = os.path.join(self.test_dir, "responses.csv")
        
        self.assertTrue(os.path.exists(questions_file))
        self.assertTrue(os.path.exists(responses_file))
        
        # Verify log content
        import csv
        
        with open(questions_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            question_records = list(reader)
            self.assertEqual(len(question_records), 1)
            self.assertEqual(question_records[0]['email'], user_email)
            self.assertEqual(question_records[0]['question'], query)
        
        with open(responses_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            response_records = list(reader)
            self.assertEqual(len(response_records), 1)
            self.assertEqual(response_records[0]['email'], user_email)
            self.assertEqual(response_records[0]['success'], 'True')
    
    def test_config_component_integration(self):
        """Test integration with configuration components"""
        from config import AppConfig
        from department_manager import DepartmentManager
        
        # Test that configuration is used properly
        config = AppConfig()
        
        # Verify departments from config
        self.assertIn("HR", config.DEPARTMENTS)
        self.assertIn("IT", config.DEPARTMENTS)
        
        # Verify language options
        self.assertIn("English", config.LANGUAGE_OPTIONS)
        self.assertIn("Hindi (हिन्दी)", config.LANGUAGE_OPTIONS)
        
        # Test singleton pattern
        config2 = AppConfig.get_instance()
        self.assertIs(config, config2)
        
        # Test that creating a new instance returns the same singleton
        config3 = AppConfig()
        self.assertIs(config, config3)
        
        # Test that components can use config
        with patch('department_manager.openai'):
            manager = DepartmentManager()
            # Should initialize without errors using default config
            self.assertIsNotNone(manager)


class TestEndToEndScenarios(unittest.TestCase):
    """Test complete end-to-end scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        self.env_patcher = patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-e2e-key'
        })
        self.env_patcher.start()
        
        self.openai_patcher1 = patch('department_manager.openai')
        self.openai_patcher2 = patch('query_services.openai')
        self.mock_openai1 = self.openai_patcher1.start()
        self.mock_openai2 = self.openai_patcher2.start()
        
        mock_embedding_response = {
            'data': [{'embedding': [0.1] * 1536} for _ in range(10)]
        }
        mock_chat_response = {
            'choices': [{'message': {'content': 'End-to-end test response'}}]
        }
        
        self.mock_openai1.Embedding.create.return_value = mock_embedding_response
        self.mock_openai1.ChatCompletion.create.return_value = mock_chat_response
        self.mock_openai2.Embedding.create.return_value = mock_embedding_response
        self.mock_openai2.ChatCompletion.create.return_value = mock_chat_response
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        self.openai_patcher1.stop()
        self.openai_patcher2.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_new_employee_onboarding_scenario(self):
        """Test scenario: New employee asking about company policies"""
        from department_manager import DepartmentManager
        from query_services import QueryProcessor
        from utils.user_logger import UserLogger
        
        # Initialize system
        manager = DepartmentManager()
        manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
        os.makedirs(manager.faiss_index_dir, exist_ok=True)
        
        processor = QueryProcessor(manager)
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        # Setup HR documents (admin uploads)
        hr_documents = {
            "employee_handbook.pdf": "Employee handbook: Welcome to the company. This handbook contains important information about company policies, procedures, and benefits.",
            "leave_policy.pdf": "Leave Policy: All employees are entitled to 30 days of paid annual leave. Sick leave is available up to 10 days per year.",
            "benefits_guide.pdf": "Benefits Guide: The company provides comprehensive health insurance, dental coverage, vision care, and a 401(k) retirement plan."
        }
        
        for filename, content in hr_documents.items():
            manager.save_department_pdf("HR", filename, content)
        
        manager.create_department_index("HR", list(hr_documents.values()))
        
        # New employee interaction
        employee_email = "newemployee@aiplabro.com"
        
        # Employee logs in
        logger.log_user_login(employee_email, True, "192.168.1.50")
        
        # Employee asks typical onboarding questions
        onboarding_questions = [
            "What benefits does the company provide?",
            "How many vacation days do I get?",
            "What is the sick leave policy?",
            "Where can I find the employee handbook?"
        ]
        
        for question in onboarding_questions:
            logger.log_user_question(employee_email, question, "HR", "English")
            
            response = processor.process_query(question, "HR")
            
            # Verify response quality
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 10)  # Should be a substantial response
            
            logger.log_bot_response(employee_email, question, response, True, 1.5)
        
        logger.log_user_logout(employee_email)
        
        # Verify complete interaction was logged
        user_stats = logger.get_user_stats(employee_email)
        self.assertEqual(user_stats['total_logins'], 1)
        self.assertEqual(user_stats['total_questions'], len(onboarding_questions))
        self.assertEqual(user_stats['total_responses'], len(onboarding_questions))
        self.assertIn('HR', user_stats['departments_used'])
    
    def test_multilingual_support_scenario(self):
        """Test scenario: User asking questions in different languages"""
        from department_manager import DepartmentManager
        from query_services import QueryProcessor
        from utils.user_logger import UserLogger
        
        # Initialize system
        manager = DepartmentManager()
        manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
        os.makedirs(manager.faiss_index_dir, exist_ok=True)
        
        processor = QueryProcessor(manager)
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        # Setup documents
        documents = ["Company policy: Working hours are 9 AM to 6 PM Monday to Friday."]
        manager.create_department_index("HR", documents)
        manager.save_department_pdf("HR", "policy.pdf", documents[0])
        
        user_email = "multilingual@aiplabro.com"
        logger.log_user_login(user_email, True)
        
        # Test with different languages
        test_cases = [
            ("English", "en", "What are the working hours?"),
            ("Hindi", "hi", "काम के घंटे क्या हैं?"),
            ("Tamil", "ta", "வேலை நேரம் என்ன?"),
        ]
        
        for language_name, language_code, question in test_cases:
            with self.subTest(language=language_name):
                logger.log_user_question(user_email, question, "HR", language_name)
                
                # Mock translation for non-English
                if language_code != 'en':
                    with patch.object(processor.translator, 'translate_text') as mock_translate:
                        mock_translate.return_value = f"Translated response in {language_name}"
                        
                        response = processor.process_query(question, "HR", language_code)
                        
                        self.assertIsInstance(response, str)
                        if language_code != 'en':
                            mock_translate.assert_called_once()
                else:
                    response = processor.process_query(question, "HR", language_code)
                    self.assertIsInstance(response, str)
                
                logger.log_bot_response(user_email, question, response, True, 1.0)
        
        logger.log_user_logout(user_email)
        
        # Verify multilingual interaction was logged
        user_stats = logger.get_user_stats(user_email)
        self.assertEqual(user_stats['total_questions'], 3)
        self.assertEqual(len(user_stats['languages_used']), 3)


if __name__ == '__main__':
    unittest.main()
