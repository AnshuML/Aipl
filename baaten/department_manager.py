import os
import numpy as np
import faiss
from dotenv import load_dotenv
import openai
import glob

class DepartmentManager:
    def __init__(self):
        self.departments = {}
        load_dotenv()
        self.openai_api_key = self._get_openai_api_key()
        self.embedding_model = "text-embedding-3-large"
        
        # Define base directory path - handle both local and cloud deployment
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # For Streamlit Cloud, use a more reliable path
        if os.path.exists("/mount/src"):
            # Streamlit Cloud environment
            self.faiss_index_dir = os.path.join(self.base_dir, "faiss_index")
        else:
            # Local environment
            self.faiss_index_dir = os.path.join(self.base_dir, "faiss_index")
        
        print(f"Department Manager initialized with base_dir: {self.base_dir}")
        print(f"FAISS index directory: {self.faiss_index_dir}")
        
        # Initialize departments dictionary with available indexes
        self._initialize_departments()

    def get_openai_embeddings(self, texts):
        import time
        from openai import OpenAI
        
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                client = OpenAI(api_key=self.openai_api_key)
                response = client.embeddings.create(
                    input=texts,
                    model=self.embedding_model
                )
                return [d.embedding for d in response.data]
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Embedding generation attempt {attempt + 1} failed: {str(e)}. Retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise Exception(f"Failed to generate embeddings after {max_retries} attempts: {str(e)}")

    def _get_openai_api_key(self) -> str:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            try:
                import streamlit as st
                key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
            except Exception:
                key = None
        if not key:
            raise ValueError("OPENAI_API_KEY not set in environment or Streamlit secrets.")
        if isinstance(key, str):
            # Remove quotes and whitespace
            key = key.strip()
            if key.startswith('"') and key.endswith('"'):
                key = key[1:-1]
            elif key.startswith("'") and key.endswith("'"):
                key = key[1:-1]
            key = key.strip()
        return key

    def create_department_index(self, department_name, documents):
        embeddings = self.get_openai_embeddings(documents)
        dim = len(embeddings[0])
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(embeddings).astype('float32'))
        os.makedirs(self.faiss_index_dir, exist_ok=True)
        index_path = os.path.join(self.faiss_index_dir, f"{department_name.lower()}.index")
        faiss.write_index(index, index_path)
        self.departments[department_name] = index_path
        # Save docs for BM25/hybrid retrieval (now handled per-PDF)
        # os.makedirs("faiss_index/docs", exist_ok=True)
        # with open(f"faiss_index/docs/{department_name.lower()}.txt", "w", encoding="utf-8") as f:
        #     for doc in documents:
        #         f.write(doc.replace("\n", " ").strip() + "\n")

    def get_department_docs(self, department_name):
        docs_dir = os.path.join(self.faiss_index_dir, "docs")
        
        # Debug: Print the directory we're looking in
        print(f"Looking for documents in: {docs_dir}")
        print(f"Department: {department_name}")
        
        # Check if docs directory exists
        if not os.path.exists(docs_dir):
            print(f"Docs directory does not exist: {docs_dir}")
            # Try alternative paths for Streamlit Cloud
            alternative_paths = [
                os.path.join(self.base_dir, "faiss_index", "docs"),
                os.path.join("/tmp", "faiss_index", "docs"),
                os.path.join(os.getcwd(), "faiss_index", "docs")
            ]
            
            for alt_path in alternative_paths:
                if os.path.exists(alt_path):
                    docs_dir = alt_path
                    print(f"Found alternative docs directory: {docs_dir}")
                    break
            else:
                print("No docs directory found in any location")
                return []
        
        # List all files in docs directory for debugging
        try:
            all_files = os.listdir(docs_dir)
            print(f"All files in docs directory: {all_files}")
        except Exception as e:
            print(f"Error listing files in {docs_dir}: {str(e)}")
            return []
        
        # Try multiple patterns to find department files
        patterns = [
            f"{department_name.lower()}_*.txt",  # hr_*.txt
            f"{department_name.lower()}*.txt",   # hr*.txt
            f"{department_name.lower()}.txt",    # hr.txt
            f"{department_name.upper()}_*.txt",  # HR_*.txt
            f"{department_name.upper()}*.txt",   # HR*.txt
            f"{department_name.upper()}.txt"     # HR.txt
        ]
        
        files = []
        for pattern in patterns:
            pattern_path = os.path.join(docs_dir, pattern)
            found_files = glob.glob(pattern_path)
            if found_files:
                files.extend(found_files)
                print(f"Found files with pattern {pattern}: {found_files}")
        
        # Remove duplicates
        files = list(set(files))
        
        docs = []
        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:  # Only add non-empty content
                        docs.append(content)
                        print(f"Successfully loaded document: {os.path.basename(file)}")
            except Exception as e:
                print(f"Error reading file {file}: {str(e)}")
        
        print(f"Total documents loaded for {department_name}: {len(docs)}")
        return docs

    def get_department_index(self, department_name):
        path = self.departments.get(department_name)
        if not path or not os.path.exists(path):
            # Try to find the index file directly in the faiss_index directory
            direct_path = os.path.join(self.faiss_index_dir, f"{department_name.lower()}.index")
            if os.path.exists(direct_path):
                # Add it to the departments dictionary for future reference
                self.departments[department_name] = direct_path
                return faiss.read_index(direct_path)
            
            # Also check for department subdirectory with index.faiss
            dept_dir = os.path.join(self.faiss_index_dir, department_name.lower())
            if os.path.exists(dept_dir) and os.path.isdir(dept_dir):
                index_path = os.path.join(dept_dir, "index.faiss")
                if os.path.exists(index_path):
                    self.departments[department_name] = index_path
                    return faiss.read_index(index_path)
            return None
        return faiss.read_index(path)

    # --- New methods for per-PDF management ---
    def save_department_pdf(self, department_name, pdf_filename, text):
        # Sanitize department name and filename to prevent path traversal
        safe_dept_name = self._sanitize_name(department_name)
        safe_filename = self._sanitize_name(pdf_filename)
        
        docs_dir = os.path.join(self.faiss_index_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        path = os.path.join(docs_dir, f"{safe_dept_name}_{safe_filename}.txt")
        
        # Ensure the path is within the docs directory
        if not os.path.abspath(path).startswith(os.path.abspath(docs_dir)):
            raise ValueError("Invalid path: potential path traversal detected")
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text.strip())
            print(f"Successfully saved document: {path}")
            
            # Also save to a backup location for Streamlit Cloud persistence
            backup_dir = os.path.join("/tmp", "faiss_index", "docs")
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f"{safe_dept_name}_{safe_filename}.txt")
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(text.strip())
            print(f"Successfully saved backup document: {backup_path}")
            
        except Exception as e:
            print(f"Error saving document {path}: {str(e)}")
            raise
    
    def _sanitize_name(self, name):
        """Sanitize department name or filename to prevent path traversal"""
        import re
        # Remove path traversal attempts
        name = re.sub(r'[\.]{2,}', '', name)
        # Remove dangerous characters
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Remove leading/trailing dots and spaces
        name = name.strip('. ')
        # Ensure it's not empty
        if not name:
            name = "default"
        return name.lower()

    def list_department_pdfs(self, department_name):
        docs_dir = os.path.join(self.faiss_index_dir, "docs")
        pattern = os.path.join(docs_dir, f"{department_name.lower()}_*.txt")
        files = glob.glob(pattern)
        return [os.path.basename(f).replace(f"{department_name.lower()}_", "").replace('.txt','') for f in files]

    def delete_department_pdf(self, department_name, pdf_filename):
        docs_dir = os.path.join(self.faiss_index_dir, "docs")
        path = os.path.join(docs_dir, f"{department_name.lower()}_{pdf_filename}.txt")
        if os.path.exists(path):
            os.remove(path)
            # Optionally: Rebuild the index after deletion
            self.rebuild_department_index(department_name)

    def _initialize_departments(self):
        """Scan for available department indexes and initialize the departments dictionary."""
        # Create faiss_index directory if it doesn't exist
        os.makedirs(self.faiss_index_dir, exist_ok=True)
        
        # Check for department directories with index.faiss files
        try:
            for item in os.listdir(self.faiss_index_dir):
                item_path = os.path.join(self.faiss_index_dir, item)
                if os.path.isdir(item_path) and item != "docs":
                    index_path = os.path.join(item_path, "index.faiss")
                    if os.path.exists(index_path):
                        self.departments[item.capitalize()] = index_path
            
            # Check for direct .index files in the faiss_index directory
            for item in os.listdir(self.faiss_index_dir):
                if item.endswith(".index"):
                    department_name = item.replace(".index", "").capitalize()
                    self.departments[department_name] = os.path.join(self.faiss_index_dir, item)
        except FileNotFoundError as e:
            print(f"Error initializing departments: {str(e)}")
            # Create the directory if it doesn't exist
            os.makedirs(self.faiss_index_dir, exist_ok=True)
    
    def rebuild_department_index(self, department_name):
        docs_dir = os.path.join(self.faiss_index_dir, "docs")
        pattern = os.path.join(docs_dir, f"{department_name.lower()}_*.txt")
        files = glob.glob(pattern)
        documents = []
        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    documents.append(f.read())
            except Exception as e:
                print(f"Error reading file {file}: {str(e)}")
        if documents:
            self.create_department_index(department_name, documents)
        else:
            # Remove index if no documents left
            index_path = os.path.join(self.faiss_index_dir, f"{department_name.lower()}.index")
            if os.path.exists(index_path):
                os.remove(index_path)
