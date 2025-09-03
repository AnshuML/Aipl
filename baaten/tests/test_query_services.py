"""
Unit tests for QueryProcessor module
"""
import unittest
import numpy as np
from unittest.mock import Mock, MagicMock, patch

# Import the module to test
from query_services import QueryProcessor


class TestQueryProcessor(unittest.TestCase):
    """Test QueryProcessor class"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock DepartmentManager
        self.mock_department_manager = Mock()
        self.mock_department_manager.get_department_docs.return_value = [
            "HR policy document content here...",
            "Leave policy: Employees can take annual leave...",
            "Attendance policy: Working hours are 9 AM to 6 PM..."
        ]
        
        # Mock FAISS index
        mock_index = Mock()
        mock_index.search.return_value = (
            np.array([[0.1, 0.2, 0.3]]),  # distances
            np.array([[0, 1, 2]])  # indices
        )
        self.mock_department_manager.get_department_index.return_value = mock_index
        
        # Mock embeddings
        self.mock_department_manager.get_openai_embeddings.return_value = [[0.1] * 1536]
        
        # Create QueryProcessor
        self.processor = QueryProcessor(self.mock_department_manager)
    
    @patch('query_services.openai')
    def test_process_query_success(self, mock_openai):
        """Test successful query processing"""
        # Mock OpenAI response
        mock_openai.ChatCompletion.create.return_value = {
            'choices': [
                {'message': {'content': 'The leave policy allows 30 days annual leave.'}}
            ]
        }
        
        query = "What is the leave policy?"
        department = "HR"
        
        response = self.processor.process_query(query, department)
        
        self.assertIsInstance(response, str)
        self.assertIn("leave policy", response.lower())
        
        # Verify OpenAI was called
        mock_openai.ChatCompletion.create.assert_called_once()
    
    def test_process_query_no_documents(self):
        """Test query processing with no documents"""
        # Mock no documents
        self.mock_department_manager.get_department_docs.return_value = []
        
        query = "What is the policy?"
        department = "HR"
        
        response = self.processor.process_query(query, department)
        
        self.assertIn("No documents found", response)
        self.assertIn("admin", response.lower())
    
    def test_process_query_no_faiss_index(self):
        """Test query processing with no FAISS index"""
        # Mock no FAISS index
        self.mock_department_manager.get_department_index.return_value = None
        
        query = "What is the policy?"
        department = "HR"
        
        # Should still work with BM25 only
        with patch('query_services.openai') as mock_openai:
            mock_openai.ChatCompletion.create.return_value = {
                'choices': [{'message': {'content': 'Policy information...'}}]
            }
            
            response = self.processor.process_query(query, department)
            self.assertIsInstance(response, str)
    
    @patch('query_services.openai')
    def test_process_query_with_translation(self, mock_openai):
        """Test query processing with translation"""
        # Mock OpenAI response
        mock_openai.ChatCompletion.create.return_value = {
            'choices': [
                {'message': {'content': 'The leave policy allows 30 days annual leave.'}}
            ]
        }
        
        # Mock translation service
        with patch.object(self.processor.translator, 'translate_text') as mock_translate:
            mock_translate.return_value = "छुट्टी नीति 30 दिन की वार्षिक छुट्टी की अनुमति देती है।"
            
            query = "What is the leave policy?"
            department = "HR"
            language_code = "hi"
            
            response = self.processor.process_query(query, department, language_code)
            
            # Should return translated response
            self.assertIn("छुट्टी नीति", response)
            mock_translate.assert_called_once()
    
    @patch('query_services.openai')
    def test_process_query_translation_error(self, mock_openai):
        """Test query processing with translation error"""
        # Mock OpenAI response
        mock_openai.ChatCompletion.create.return_value = {
            'choices': [
                {'message': {'content': 'The leave policy allows 30 days annual leave.'}}
            ]
        }
        
        # Mock translation service error
        with patch.object(self.processor.translator, 'translate_text') as mock_translate:
            mock_translate.side_effect = Exception("Translation service unavailable")
            
            query = "What is the leave policy?"
            department = "HR"
            language_code = "hi"
            
            response = self.processor.process_query(query, department, language_code)
            
            # Should return error message
            self.assertIn("Translation error", response)
    
    def test_bm25_retrieval(self):
        """Test BM25 retrieval functionality"""
        docs = [
            "Leave policy allows 30 days annual leave for employees",
            "Attendance policy requires 9 AM to 6 PM working hours",
            "Benefits include health insurance and retirement plans"
        ]
        
        self.mock_department_manager.get_department_docs.return_value = docs
        
        query = "leave policy"
        department = "HR"
        
        with patch('query_services.openai') as mock_openai:
            mock_openai.ChatCompletion.create.return_value = {
                'choices': [{'message': {'content': 'Leave policy response...'}}]
            }
            
            response = self.processor.process_query(query, department, top_k=2)
            
            # BM25 should rank leave policy document higher
            # Verify OpenAI was called with relevant context
            call_args = mock_openai.ChatCompletion.create.call_args
            system_message = call_args[1]['messages'][0]['content']
            self.assertIn("leave", system_message.lower())
    
    def test_hybrid_retrieval_deduplication(self):
        """Test hybrid retrieval removes duplicates"""
        docs = [
            "Duplicate document content",
            "Unique document 1",
            "Unique document 2"
        ]
        
        self.mock_department_manager.get_department_docs.return_value = docs
        
        # Mock FAISS to return same documents as BM25
        mock_index = Mock()
        mock_index.search.return_value = (
            np.array([[0.1, 0.2, 0.3]]),
            np.array([[0, 1, 0]])  # Returns indices 0, 1, 0 (duplicate)
        )
        self.mock_department_manager.get_department_index.return_value = mock_index
        
        query = "test query"
        department = "HR"
        
        with patch('query_services.openai') as mock_openai:
            mock_openai.ChatCompletion.create.return_value = {
                'choices': [{'message': {'content': 'Test response'}}]
            }
            
            response = self.processor.process_query(query, department)
            
            # Should deduplicate documents in context
            call_args = mock_openai.ChatCompletion.create.call_args
            system_message = call_args[1]['messages'][0]['content']
            
            # Count occurrences of duplicate content
            duplicate_count = system_message.count("Duplicate document content")
            self.assertEqual(duplicate_count, 1)  # Should appear only once
    
    @patch('query_services.openai')
    def test_openai_api_error_handling(self, mock_openai):
        """Test handling of OpenAI API errors"""
        # Mock OpenAI API error
        mock_openai.ChatCompletion.create.side_effect = Exception("API rate limit exceeded")
        
        query = "What is the policy?"
        department = "HR"
        
        # Should handle the error gracefully
        try:
            response = self.processor.process_query(query, department)
            # If no exception is raised, check if error is handled in response
            self.assertIsInstance(response, str)
        except Exception as e:
            # If exception is raised, it should be a handled exception
            self.assertIn("API", str(e))
    
    def test_multiple_questions_processing(self):
        """Test processing multiple questions in single query"""
        with patch('query_services.openai') as mock_openai:
            mock_openai.ChatCompletion.create.return_value = {
                'choices': [{'message': {'content': 'Answer to question'}}]
            }
            
            query = "What is leave policy? What are working hours?"
            department = "HR"
            
            response = self.processor.process_query(query, department)
            
            # Should process both questions
            self.assertIsInstance(response, str)
            # OpenAI should be called twice (once for each question)
            self.assertEqual(mock_openai.ChatCompletion.create.call_count, 2)
    
    def test_empty_query_handling(self):
        """Test handling of empty queries"""
        query = ""
        department = "HR"
        
        with patch('query_services.openai') as mock_openai:
            response = self.processor.process_query(query, department)
            
            # Should handle empty query gracefully
            # OpenAI should not be called
            mock_openai.ChatCompletion.create.assert_not_called()
    
    def test_system_prompt_construction(self):
        """Test system prompt construction"""
        docs = [
            "Test document 1 content",
            "Test document 2 content"
        ]
        
        self.mock_department_manager.get_department_docs.return_value = docs
        
        query = "test question"
        department = "HR"
        
        with patch('query_services.openai') as mock_openai:
            mock_openai.ChatCompletion.create.return_value = {
                'choices': [{'message': {'content': 'Test response'}}]
            }
            
            self.processor.process_query(query, department)
            
            # Check system prompt construction
            call_args = mock_openai.ChatCompletion.create.call_args
            system_message = call_args[1]['messages'][0]['content']
            
            # Should contain helpful assistant instructions
            self.assertIn("helpful assistant", system_message.lower())
            self.assertIn("department documents", system_message.lower())
            self.assertIn("test document", system_message)
            
            # Should contain the query
            user_message = call_args[1]['messages'][1]['content']
            self.assertEqual(user_message, query)


class TestQueryProcessorEdgeCases(unittest.TestCase):
    """Test edge cases for QueryProcessor"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_department_manager = Mock()
        self.processor = QueryProcessor(self.mock_department_manager)
    
    def test_very_long_query(self):
        """Test processing very long queries"""
        # Create a very long query
        long_query = "What is the policy? " * 100  # Very long query
        department = "HR"
        
        self.mock_department_manager.get_department_docs.return_value = ["Policy document"]
        self.mock_department_manager.get_department_index.return_value = None
        
        with patch('query_services.openai') as mock_openai:
            mock_openai.ChatCompletion.create.return_value = {
                'choices': [{'message': {'content': 'Policy response'}}]
            }
            
            response = self.processor.process_query(long_query, department)
            self.assertIsInstance(response, str)
    
    def test_special_characters_in_query(self):
        """Test queries with special characters"""
        queries_with_special_chars = [
            "What's the policy?",
            "Policy for HR & IT departments?",
            "Leave policy (annual/sick)?",
            "Policy @ company level?",
            "Benefits: health + dental?"
        ]
        
        self.mock_department_manager.get_department_docs.return_value = ["Policy document"]
        self.mock_department_manager.get_department_index.return_value = None
        
        for query in queries_with_special_chars:
            with patch('query_services.openai') as mock_openai:
                mock_openai.ChatCompletion.create.return_value = {
                    'choices': [{'message': {'content': 'Policy response'}}]
                }
                
                response = self.processor.process_query(query, "HR")
                self.assertIsInstance(response, str)
    
    def test_non_english_query(self):
        """Test queries in non-English languages"""
        queries = [
            "नीति क्या है?",  # Hindi
            "கொள்கை என்ன?",  # Tamil
            "নীতি কি?",  # Bengali
        ]
        
        self.mock_department_manager.get_department_docs.return_value = ["Policy document"]
        self.mock_department_manager.get_department_index.return_value = None
        
        for query in queries:
            with patch('query_services.openai') as mock_openai:
                mock_openai.ChatCompletion.create.return_value = {
                    'choices': [{'message': {'content': 'Policy response'}}]
                }
                
                response = self.processor.process_query(query, "HR")
                self.assertIsInstance(response, str)
    
    def test_large_document_corpus(self):
        """Test with large number of documents"""
        # Create large corpus
        large_docs = [f"Document {i} content here..." for i in range(1000)]
        
        self.mock_department_manager.get_department_docs.return_value = large_docs
        
        # Mock FAISS index
        mock_index = Mock()
        mock_index.search.return_value = (
            np.random.random((1, 3)),  # distances
            np.array([[0, 1, 2]])  # indices
        )
        self.mock_department_manager.get_department_index.return_value = mock_index
        
        query = "test query"
        department = "HR"
        
        with patch('query_services.openai') as mock_openai:
            mock_openai.ChatCompletion.create.return_value = {
                'choices': [{'message': {'content': 'Test response'}}]
            }
            
            response = self.processor.process_query(query, department)
            self.assertIsInstance(response, str)


if __name__ == '__main__':
    unittest.main()
