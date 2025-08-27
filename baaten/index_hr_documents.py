#!/usr/bin/env python3
"""
Script to properly index HR policy documents for the chatbot system.
This script reads the text files (with .pdf extensions) and creates a FAISS index.
"""

import os
import sys
from pathlib import Path
from typing import List
from department_manager import DepartmentManager

class Config:
    """Configuration constants for HR document indexing"""
    HR_POLICIES_DIR = "hr_policies"
    DEPARTMENT_NAME = "HR"
    FILE_PATTERN = "*.pdf"
    ENCODING = "utf-8"
    DOCUMENT_SEPARATOR = "==="

def read_hr_documents() -> List[str]:
    """Read all HR policy documents from the hr_policies folder"""
    hr_policies_dir = Path(Config.HR_POLICIES_DIR)
    documents = []
    
    if not hr_policies_dir.exists():
        print(f"❌ HR policies directory not found: {hr_policies_dir.absolute()}")
        return []
    
    print("📖 Reading HR policy documents...")
    
    for file_path in hr_policies_dir.glob(Config.FILE_PATTERN):
        try:
            print(f"  📄 Reading: {file_path.name}")
            with open(file_path, 'r', encoding=Config.ENCODING) as f:
                content = f.read().strip()
                
                if not content:
                    print(f"  ⚠️  Warning: {file_path.name} is empty, skipping...")
                    continue
                
                # Add document title and content with better formatting
                doc_text = f"{Config.DOCUMENT_SEPARATOR} {file_path.stem.replace('_', ' ').title()} {Config.DOCUMENT_SEPARATOR}\n\n{content}"
                documents.append(doc_text)
                print(f"    ✅ Added {len(content):,} characters")
                
        except UnicodeDecodeError as e:
            print(f"  ❌ Encoding error reading {file_path.name}: {e}")
        except FileNotFoundError as e:
            print(f"  ❌ File not found {file_path.name}: {e}")
        except PermissionError as e:
            print(f"  ❌ Permission denied reading {file_path.name}: {e}")
        except Exception as e:
            print(f"  ❌ Unexpected error reading {file_path.name}: {e}")
    
    print(f"📊 Total documents processed: {len(documents)}")
    return documents

def create_hr_index(documents: List[str]) -> bool:
    """Create HR department index from documents"""
    try:
        print("🔧 Initializing department manager...")
        dept_manager = DepartmentManager()
        
        print("🧠 Initializing embeddings...")
        dept_manager.init_embeddings()
        
        print(f"📚 Creating {Config.DEPARTMENT_NAME} department index...")
        dept_manager.create_department_index(Config.DEPARTMENT_NAME, documents)
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during indexing: {e}")
        return False

def main() -> int:
    """Main function to index HR documents"""
    print("🚀 Starting HR document indexing...")
    
    try:
        # Read HR documents
        documents = read_hr_documents()
        
        if not documents:
            print("❌ No documents found to index!")
            return 1
        
        # Create index
        if create_hr_index(documents):
            print("✅ HR documents indexed successfully!")
            print(f"📊 Indexed {len(documents)} documents for {Config.DEPARTMENT_NAME} department")
            return 0
        else:
            print("❌ Failed to create HR index")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Indexing interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())