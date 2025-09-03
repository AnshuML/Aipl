"""
Unit tests for DepartmentManager module
"""
import unittest
import os
import tempfile
import shutil
import numpy as np
import faiss
from unittest.mock import patch, MagicMock

# Import the module to test
from department_manager import DepartmentManager


class TestDepartmentManager(unittest.TestCase):
    """Test DepartmentManager class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-api-key-12345'
        })
        self.env_patcher.start()
        
        # Mock OpenAI API calls
        self.openai_patcher = patch('department_manager.openai')
        self.mock_openai = self.openai_patcher.start()
        
        # Mock embedding response
        mock_embedding_response = {
            'data': [
                {'embedding': [0.1] * 1536},  # Mock 1536-dim embedding
                {'embedding': [0.2] * 1536},
                {'embedding': [0.3] * 1536}
            ]
        }
        self.mock_openai.Embedding.create.return_value = mock_embedding_response
        
        # Create DepartmentManager with custom test directory
        self.manager = DepartmentManager()
        self.manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
        os.makedirs(self.manager.faiss_index_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        self.openai_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test DepartmentManager initialization"""
        self.assertIsInstance(self.manager.departments, dict)
        self.assertEqual(self.manager.embedding_model, "text-embedding-3-large")
        self.assertIsNotNone(self.manager.openai_api_key)
    
    def test_get_openai_api_key_from_env(self):
        """Test getting OpenAI API key from environment"""
        key = self.manager._get_openai_api_key()
        self.assertEqual(key, 'test-api-key-12345')
    
    def test_get_openai_api_key_missing(self):
        """Test error when OpenAI API key is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                DepartmentManager()
    
    @patch('department_manager.st')
    def test_get_openai_api_key_from_streamlit_secrets(self, mock_st):
        """Test getting API key from Streamlit secrets"""
        with patch.dict(os.environ, {}, clear=True):
            mock_st.secrets.get.return_value = 'streamlit-secret-key'
            manager = DepartmentManager()
            self.assertEqual(manager.openai_api_key, 'streamlit-secret-key')
    
    def test_get_openai_embeddings(self):
        """Test OpenAI embeddings generation"""
        texts = ["Test document 1", "Test document 2", "Test document 3"]
        embeddings = self.manager.get_openai_embeddings(texts)
        
        self.assertEqual(len(embeddings), 3)
        self.assertEqual(len(embeddings[0]), 1536)  # Expected embedding dimension
        
        # Verify OpenAI API was called correctly
        self.mock_openai.Embedding.create.assert_called_once_with(
            input=texts,
            model="text-embedding-3-large"
        )
    
    def test_create_department_index(self):
        """Test creating department index"""
        department = "HR"
        documents = ["HR policy document", "Leave policy", "Employee handbook"]
        
        self.manager.create_department_index(department, documents)
        
        # Check if index file was created
        index_path = os.path.join(self.manager.faiss_index_dir, f"{department.lower()}.index")
        self.assertTrue(os.path.exists(index_path))
        
        # Verify department was added to departments dict
        self.assertIn(department, self.manager.departments)
        self.assertEqual(self.manager.departments[department], index_path)
    
    def test_get_department_index_existing(self):
        """Test getting existing department index"""
        department = "HR"
        documents = ["HR policy document", "Leave policy"]
        
        # Create index first
        self.manager.create_department_index(department, documents)
        
        # Retrieve index
        index = self.manager.get_department_index(department)
        self.assertIsNotNone(index)
        self.assertIsInstance(index, faiss.IndexFlatL2)
    
    def test_get_department_index_nonexistent(self):
        """Test getting non-existent department index"""
        index = self.manager.get_department_index("NonExistent")
        self.assertIsNone(index)
    
    def test_get_department_index_direct_path(self):
        """Test getting index using direct path discovery"""
        department = "Accounts"
        documents = ["Account policy", "Financial procedures"]
        
        # Create index file directly
        self.manager.create_department_index(department, documents)
        
        # Clear departments dict to test direct path discovery
        self.manager.departments.clear()
        
        # Should still find the index file
        index = self.manager.get_department_index(department)
        self.assertIsNotNone(index)
    
    def test_save_department_pdf(self):
        """Test saving department PDF content"""
        department = "IT"
        pdf_filename = "security_policy.pdf"
        text_content = "IT security policy content here..."
        
        self.manager.save_department_pdf(department, pdf_filename, text_content)
        
        # Check if file was saved
        docs_dir = os.path.join(self.manager.faiss_index_dir, "docs")
        expected_file = os.path.join(docs_dir, f"{department.lower()}_{pdf_filename}.txt")
        self.assertTrue(os.path.exists(expected_file))
        
        # Verify content
        with open(expected_file, 'r', encoding='utf-8') as f:
            saved_content = f.read()
            self.assertEqual(saved_content.strip(), text_content.strip())
    
    def test_list_department_pdfs(self):
        """Test listing department PDFs"""
        department = "Sales"
        
        # Save multiple PDFs
        pdf_files = ["sales_guide.pdf", "pricing_policy.pdf", "commission_structure.pdf"]
        for pdf_file in pdf_files:
            self.manager.save_department_pdf(department, pdf_file, f"Content of {pdf_file}")
        
        # List PDFs
        listed_pdfs = self.manager.list_department_pdfs(department)
        
        self.assertEqual(len(listed_pdfs), 3)
        self.assertIn("sales_guide.pdf", listed_pdfs)
        self.assertIn("pricing_policy.pdf", listed_pdfs)
        self.assertIn("commission_structure.pdf", listed_pdfs)
    
    def test_list_department_pdfs_empty(self):
        """Test listing PDFs for department with no files"""
        listed_pdfs = self.manager.list_department_pdfs("EmptyDepartment")
        self.assertEqual(len(listed_pdfs), 0)
    
    def test_delete_department_pdf(self):
        """Test deleting department PDF"""
        department = "Marketing"
        pdf_filename = "brand_guidelines.pdf"
        text_content = "Brand guidelines content..."
        
        # Save PDF first
        self.manager.save_department_pdf(department, pdf_filename, text_content)
        
        # Verify it exists
        docs_dir = os.path.join(self.manager.faiss_index_dir, "docs")
        pdf_file_path = os.path.join(docs_dir, f"{department.lower()}_{pdf_filename}.txt")
        self.assertTrue(os.path.exists(pdf_file_path))
        
        # Delete PDF
        with patch.object(self.manager, 'rebuild_department_index') as mock_rebuild:
            self.manager.delete_department_pdf(department, pdf_filename)
            mock_rebuild.assert_called_once_with(department)
        
        # Verify it's deleted
        self.assertFalse(os.path.exists(pdf_file_path))
    
    def test_get_department_docs(self):
        """Test getting department documents"""
        department = "Operations"
        
        # Save multiple PDFs
        pdf_contents = {
            "procedures.pdf": "Standard operating procedures...",
            "workflows.pdf": "Workflow documentation...",
            "guidelines.pdf": "Operational guidelines..."
        }
        
        for pdf_file, content in pdf_contents.items():
            self.manager.save_department_pdf(department, pdf_file, content)
        
        # Get documents
        docs = self.manager.get_department_docs(department)
        
        self.assertEqual(len(docs), 3)
        for content in pdf_contents.values():
            self.assertIn(content, docs)
    
    def test_get_department_docs_single_file(self):
        """Test getting department docs with single department file"""
        department = "Legal"
        content = "Legal department policies and procedures..."
        
        # Create single department file (legacy format)
        docs_dir = os.path.join(self.manager.faiss_index_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        single_file = os.path.join(docs_dir, f"{department.lower()}.txt")
        
        with open(single_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Get documents
        docs = self.manager.get_department_docs(department)
        
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0], content)
    
    def test_rebuild_department_index(self):
        """Test rebuilding department index"""
        department = "Finance"
        
        # Save multiple PDFs
        pdf_files = ["budget.pdf", "forecast.pdf"]
        for pdf_file in pdf_files:
            self.manager.save_department_pdf(department, pdf_file, f"Content of {pdf_file}")
        
        # Rebuild index
        self.manager.rebuild_department_index(department)
        
        # Verify index was created
        index_path = os.path.join(self.manager.faiss_index_dir, f"{department.lower()}.index")
        self.assertTrue(os.path.exists(index_path))
        
        # Verify department is in departments dict
        self.assertIn(department, self.manager.departments)
    
    def test_rebuild_department_index_no_documents(self):
        """Test rebuilding index with no documents"""
        department = "EmptyDept"
        
        # Try to rebuild index with no documents
        self.manager.rebuild_department_index(department)
        
        # Index should be removed if it existed
        index_path = os.path.join(self.manager.faiss_index_dir, f"{department.lower()}.index")
        self.assertFalse(os.path.exists(index_path))
    
    def test_initialize_departments_with_existing_indexes(self):
        """Test department initialization with existing index files"""
        # Create some index files
        departments = ["HR", "IT", "Finance"]
        for dept in departments:
            index_path = os.path.join(self.manager.faiss_index_dir, f"{dept.lower()}.index")
            
            # Create a dummy FAISS index
            dimension = 1536
            index = faiss.IndexFlatL2(dimension)
            dummy_vector = np.random.random((1, dimension)).astype('float32')
            index.add(dummy_vector)
            faiss.write_index(index, index_path)
        
        # Re-initialize departments
        self.manager._initialize_departments()
        
        # Check if departments were discovered
        for dept in departments:
            self.assertIn(dept.capitalize(), self.manager.departments)
    
    def test_error_handling_file_operations(self):
        """Test error handling in file operations"""
        department = "TestDept"
        
        # Test with invalid file path (should handle gracefully)
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            # Should not raise exception
            docs = self.manager.get_department_docs(department)
            self.assertEqual(len(docs), 0)


class TestDepartmentManagerIntegration(unittest.TestCase):
    """Integration tests for DepartmentManager"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        # Mock environment and OpenAI
        self.env_patcher = patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-integration-key'
        })
        self.env_patcher.start()
        
        self.openai_patcher = patch('department_manager.openai')
        self.mock_openai = self.openai_patcher.start()
        
        # Mock realistic embeddings
        def mock_embedding_create(input, model):
            embeddings = []
            for i, text in enumerate(input):
                # Create somewhat realistic embeddings based on text
                embedding = [0.1 + i * 0.1] * 1536
                embeddings.append({'embedding': embedding})
            return {'data': embeddings}
        
        self.mock_openai.Embedding.create.side_effect = mock_embedding_create
        
        self.manager = DepartmentManager()
        self.manager.faiss_index_dir = os.path.join(self.test_dir, "faiss_index")
        os.makedirs(self.manager.faiss_index_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        self.openai_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_complete_workflow(self):
        """Test complete department management workflow"""
        department = "HR"
        
        # Step 1: Save multiple PDFs
        pdfs = {
            "leave_policy.pdf": "Leave policy: Employees can take up to 30 days annual leave...",
            "attendance_policy.pdf": "Attendance policy: Working hours are 9 AM to 6 PM...",
            "benefits.pdf": "Employee benefits include health insurance, retirement plans..."
        }
        
        for pdf_name, content in pdfs.items():
            self.manager.save_department_pdf(department, pdf_name, content)
        
        # Step 2: Create index
        documents = list(pdfs.values())
        self.manager.create_department_index(department, documents)
        
        # Step 3: Verify index exists and works
        index = self.manager.get_department_index(department)
        self.assertIsNotNone(index)
        self.assertEqual(index.ntotal, 3)  # Should have 3 documents
        
        # Step 4: List PDFs
        pdf_list = self.manager.list_department_pdfs(department)
        self.assertEqual(len(pdf_list), 3)
        
        # Step 5: Get documents
        docs = self.manager.get_department_docs(department)
        self.assertEqual(len(docs), 3)
        
        # Step 6: Delete one PDF and rebuild
        self.manager.delete_department_pdf(department, "benefits.pdf")
        
        # Verify PDF was deleted
        pdf_list_after_delete = self.manager.list_department_pdfs(department)
        self.assertEqual(len(pdf_list_after_delete), 2)
        self.assertNotIn("benefits.pdf", pdf_list_after_delete)
        
        # Verify index was rebuilt
        index_after_rebuild = self.manager.get_department_index(department)
        self.assertIsNotNone(index_after_rebuild)
        self.assertEqual(index_after_rebuild.ntotal, 2)  # Should have 2 documents now


if __name__ == '__main__':
    unittest.main()
