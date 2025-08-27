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
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.embedding_model = "text-embedding-3-large"
        
        # Define base directory path
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.faiss_index_dir = os.path.join(self.base_dir, "faiss_index")
        
        # Initialize departments dictionary with available indexes
        self._initialize_departments()

    def get_openai_embeddings(self, texts):
        openai.api_key = self.openai_api_key
        response = openai.Embedding.create(
            input=texts,
            model=self.embedding_model
        )
        return [d['embedding'] for d in response['data']]

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
        pattern = os.path.join(docs_dir, f"{department_name.lower()}_*.txt")
        files = glob.glob(pattern)
        
        # If no specific department files found, check for a single department file
        if not files:
            single_file = os.path.join(docs_dir, f"{department_name.lower()}.txt")
            if os.path.exists(single_file):
                files = [single_file]
        
        docs = []
        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    docs.append(f.read())
            except Exception as e:
                print(f"Error reading file {file}: {str(e)}")
        
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
        docs_dir = os.path.join(self.faiss_index_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        path = os.path.join(docs_dir, f"{department_name.lower()}_{pdf_filename}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.strip())

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
