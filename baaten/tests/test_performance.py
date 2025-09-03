"""
Performance and load tests for AIPL Chatbot
"""
import unittest
import time
import threading
import concurrent.futures
from unittest.mock import Mock, patch
import tempfile
import os


class TestPerformance(unittest.TestCase):
    """Performance tests for core components"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('department_manager.openai')
    def test_department_manager_performance(self, mock_openai):
        """Test DepartmentManager performance with multiple operations"""
        from department_manager import DepartmentManager
        
        # Mock OpenAI embeddings
        mock_openai.Embedding.create.return_value = {
            'data': [{'embedding': [0.1] * 1536} for _ in range(100)]
        }
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            manager = DepartmentManager()
            manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
            os.makedirs(manager.faiss_index_dir, exist_ok=True)
            
            # Test creating multiple department indexes
            departments = ["HR", "IT", "Finance", "Sales", "Marketing"]
            documents = [f"Document {i} content..." for i in range(100)]
            
            start_time = time.time()
            
            for dept in departments:
                manager.create_department_index(dept, documents)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Should complete within reasonable time
            self.assertLess(execution_time, 30.0, f"Index creation took {execution_time:.2f}s")
            
            # Test retrieving indexes
            start_time = time.time()
            
            for dept in departments:
                index = manager.get_department_index(dept)
                self.assertIsNotNone(index)
            
            end_time = time.time()
            retrieval_time = end_time - start_time
            
            # Index retrieval should be very fast
            self.assertLess(retrieval_time, 1.0, f"Index retrieval took {retrieval_time:.2f}s")
    
    def test_user_logger_performance(self):
        """Test UserLogger performance with high volume"""
        from utils.user_logger import UserLogger
        
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        # Test logging many events
        num_events = 1000
        events_per_user = 10
        
        start_time = time.time()
        
        for user_id in range(num_events // events_per_user):
            email = f"user{user_id}@test.com"
            
            # Login
            logger.log_user_login(email, True)
            
            # Questions and responses
            for i in range(events_per_user - 2):
                logger.log_user_question(email, f"Question {i}", "HR", "English")
                logger.log_bot_response(email, f"Question {i}", f"Response {i}", True, 1.0)
            
            # Logout
            logger.log_user_logout(email)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should handle high volume efficiently
        events_per_second = num_events / execution_time
        self.assertGreater(events_per_second, 100, 
                          f"Logger performance: {events_per_second:.2f} events/second")
    
    @patch('query_services.openai')
    def test_query_processor_performance(self, mock_openai):
        """Test QueryProcessor performance"""
        from query_services import QueryProcessor
        from department_manager import DepartmentManager
        
        # Mock OpenAI response
        mock_openai.ChatCompletion.create.return_value = {
            'choices': [{'message': {'content': 'Test response'}}]
        }
        
        # Mock department manager
        mock_dept_manager = Mock()
        mock_dept_manager.get_department_docs.return_value = [
            "Document content " * 100 for _ in range(50)  # Large documents
        ]
        
        mock_index = Mock()
        mock_index.search.return_value = (
            [[0.1, 0.2, 0.3]],  # distances
            [[0, 1, 2]]  # indices
        )
        mock_dept_manager.get_department_index.return_value = mock_index
        mock_dept_manager.get_openai_embeddings.return_value = [[0.1] * 1536]
        
        processor = QueryProcessor(mock_dept_manager)
        
        # Test multiple queries
        queries = [
            "What is the leave policy?",
            "How to apply for benefits?",
            "What are working hours?",
            "How to request vacation?",
            "What is the dress code?"
        ]
        
        start_time = time.time()
        
        for query in queries * 10:  # 50 queries total
            response = processor.process_query(query, "HR")
            self.assertIsInstance(response, str)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should process queries efficiently
        queries_per_second = (len(queries) * 10) / execution_time
        self.assertGreater(queries_per_second, 5, 
                          f"Query processing: {queries_per_second:.2f} queries/second")
    
    def test_memory_usage(self):
        """Test memory usage doesn't grow excessively"""
        try:
            import psutil
            
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Simulate heavy usage
            from utils.user_logger import UserLogger
            
            logger = UserLogger()
            logger.logs_dir = self.test_dir
            
            # Log many events
            for i in range(1000):
                email = f"user{i}@test.com"
                logger.log_user_login(email, True)
                logger.log_user_question(email, "Test question", "HR", "English")
                logger.log_bot_response(email, "Test question", "Test response", True, 1.0)
                logger.log_user_logout(email)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable
            self.assertLess(memory_increase, 100, 
                           f"Memory increased by {memory_increase:.2f}MB")
            
        except ImportError:
            self.skipTest("psutil not available for memory testing")


class TestConcurrency(unittest.TestCase):
    """Concurrency and thread safety tests"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_concurrent_logging(self):
        """Test concurrent logging operations"""
        from utils.user_logger import UserLogger
        
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        errors = []
        
        def log_user_session(user_id):
            try:
                email = f"user{user_id}@test.com"
                logger.log_user_login(email, True)
                
                for i in range(5):
                    logger.log_user_question(email, f"Question {i}", "HR", "English")
                    logger.log_bot_response(email, f"Question {i}", f"Response {i}", True, 1.0)
                
                logger.log_user_logout(email)
            except Exception as e:
                errors.append(str(e))
        
        # Run concurrent logging
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(log_user_session, i) for i in range(50)]
            concurrent.futures.wait(futures)
        
        # Should not have any errors
        self.assertEqual(len(errors), 0, f"Concurrent logging errors: {errors}")
        
        # Verify log files exist and have content
        log_files = ["logins.csv", "questions.csv", "responses.csv", "logouts.csv"]
        for log_file in log_files:
            file_path = os.path.join(self.test_dir, log_file)
            self.assertTrue(os.path.exists(file_path))
            
            # Check file is not empty
            self.assertGreater(os.path.getsize(file_path), 0)
    
    @patch('query_services.openai')
    def test_concurrent_query_processing(self, mock_openai):
        """Test concurrent query processing"""
        from query_services import QueryProcessor
        
        # Mock OpenAI response
        mock_openai.ChatCompletion.create.return_value = {
            'choices': [{'message': {'content': 'Test response'}}]
        }
        
        # Mock department manager
        mock_dept_manager = Mock()
        mock_dept_manager.get_department_docs.return_value = ["Test document"]
        mock_dept_manager.get_department_index.return_value = None
        
        processor = QueryProcessor(mock_dept_manager)
        
        results = []
        errors = []
        
        def process_query(query_id):
            try:
                query = f"Test query {query_id}"
                response = processor.process_query(query, "HR")
                results.append(response)
            except Exception as e:
                errors.append(str(e))
        
        # Run concurrent queries
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_query, i) for i in range(20)]
            concurrent.futures.wait(futures)
        
        # Should not have any errors
        self.assertEqual(len(errors), 0, f"Concurrent query errors: {errors}")
        
        # Should have processed all queries
        self.assertEqual(len(results), 20)
        
        # All results should be strings
        for result in results:
            self.assertIsInstance(result, str)
    
    def test_thread_safety_user_stats(self):
        """Test thread safety of user statistics calculation"""
        from utils.user_logger import UserLogger
        
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        # Create some initial data
        test_email = "test@example.com"
        for i in range(10):
            logger.log_user_login(test_email, True)
            logger.log_user_question(test_email, f"Question {i}", "HR", "English")
            logger.log_bot_response(test_email, f"Question {i}", f"Response {i}", True, 1.0)
        
        stats_results = []
        errors = []
        
        def get_user_stats():
            try:
                stats = logger.get_user_stats(test_email)
                stats_results.append(stats)
            except Exception as e:
                errors.append(str(e))
        
        # Run concurrent stats calculations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_user_stats) for _ in range(10)]
            concurrent.futures.wait(futures)
        
        # Should not have any errors
        self.assertEqual(len(errors), 0, f"Concurrent stats errors: {errors}")
        
        # Should have consistent results
        self.assertEqual(len(stats_results), 10)
        
        # All stats should be identical
        first_stats = stats_results[0]
        for stats in stats_results[1:]:
            self.assertEqual(stats['total_logins'], first_stats['total_logins'])
            self.assertEqual(stats['total_questions'], first_stats['total_questions'])
            self.assertEqual(stats['total_responses'], first_stats['total_responses'])


class TestLoadTesting(unittest.TestCase):
    """Load testing for high volume scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_high_volume_logging(self):
        """Test logging with high volume of events"""
        from utils.user_logger import UserLogger
        
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        # Simulate high volume
        num_users = 100
        events_per_user = 20
        
        start_time = time.time()
        
        for user_id in range(num_users):
            email = f"user{user_id}@test.com"
            
            logger.log_user_login(email, True)
            
            for event_id in range(events_per_user):
                logger.log_user_question(email, f"Question {event_id}", "HR", "English")
                logger.log_bot_response(email, f"Question {event_id}", "Response", True, 1.0)
            
            logger.log_user_logout(email)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        total_events = num_users * (events_per_user * 2 + 2)  # questions + responses + login + logout
        events_per_second = total_events / execution_time
        
        print(f"High volume logging: {events_per_second:.2f} events/second")
        
        # Should handle high volume reasonably
        self.assertGreater(events_per_second, 50, "Should handle at least 50 events/second")
        
        # Verify data integrity
        import pandas as pd
        
        logins_df = pd.read_csv(os.path.join(self.test_dir, "logins.csv"))
        questions_df = pd.read_csv(os.path.join(self.test_dir, "questions.csv"))
        responses_df = pd.read_csv(os.path.join(self.test_dir, "responses.csv"))
        
        self.assertEqual(len(logins_df), num_users)
        self.assertEqual(len(questions_df), num_users * events_per_user)
        self.assertEqual(len(responses_df), num_users * events_per_user)
    
    def test_sustained_load(self):
        """Test system under sustained load"""
        from utils.user_logger import UserLogger
        
        logger = UserLogger()
        logger.logs_dir = self.test_dir
        
        # Run sustained load for a period
        duration_seconds = 10
        start_time = time.time()
        event_count = 0
        
        while time.time() - start_time < duration_seconds:
            email = f"user{event_count}@test.com"
            logger.log_user_login(email, True)
            logger.log_user_question(email, "Test question", "HR", "English")
            logger.log_bot_response(email, "Test question", "Test response", True, 1.0)
            logger.log_user_logout(email)
            event_count += 1
        
        actual_duration = time.time() - start_time
        events_per_second = (event_count * 4) / actual_duration  # 4 events per iteration
        
        print(f"Sustained load: {events_per_second:.2f} events/second over {actual_duration:.2f}s")
        
        # Should maintain reasonable performance
        self.assertGreater(events_per_second, 30, "Should maintain at least 30 events/second")


if __name__ == '__main__':
    # Run performance tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Run concurrency tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestConcurrency)
    result = runner.run(suite)
    
    # Run load tests (optional - can be resource intensive)
    if os.environ.get('RUN_LOAD_TESTS', '').lower() == 'true':
        suite = unittest.TestLoader().loadTestsFromTestCase(TestLoadTesting)
        result = runner.run(suite)
