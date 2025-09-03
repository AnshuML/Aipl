import streamlit as st
import os
import re
from query_services import QueryProcessor
from dotenv import load_dotenv
from datetime import datetime
import pytz
import random
from typing import List, Tuple, Optional, Dict, Any
# Translation handled by TranslationService with fallback
from rank_bm25 import BM25Okapi
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.retrievers import BM25Retriever
import openai

# Local imports
from config import config
from department_manager import DepartmentManager

# Import user_logger with better error handling
try:
    from utils.user_logger import user_logger
except (ImportError, KeyError, ModuleNotFoundError) as e:
    # Fallback for when utils module is not available
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    utils_path = os.path.join(current_dir, 'utils')
    if utils_path not in sys.path:
        sys.path.insert(0, utils_path)
    try:
        from user_logger import user_logger
    except ImportError:
        # Create a dummy logger if all else fails
        class DummyLogger:
            def log_user_login(self, *args, **kwargs): pass
            def log_user_question(self, *args, **kwargs): pass
            def log_bot_response(self, *args, **kwargs): pass
            def log_user_logout(self, *args, **kwargs): pass
            def log_error(self, *args, **kwargs): pass
        user_logger = DummyLogger()
        print(f"Warning: Using dummy logger due to import error: {e}")

# Cache department manager globally to prevent recreation
@st.cache_resource
def get_department_manager():
    return DepartmentManager()

# Store documents in session state for persistence
def get_department_docs_from_session(department_name):
    """Get department documents from session state or file system"""
    session_key = f"docs_{department_name.lower()}"
    
    if session_key not in st.session_state:
        # Load from file system
        dept_manager = get_department_manager()
        docs = dept_manager.get_department_docs(department_name)
        st.session_state[session_key] = docs
        print(f"Loaded {len(docs)} documents for {department_name} into session state")
    
    return st.session_state[session_key]

def save_department_docs_to_session(department_name, docs):
    """Save department documents to session state"""
    session_key = f"docs_{department_name.lower()}"
    st.session_state[session_key] = docs
    print(f"Saved {len(docs)} documents for {department_name} to session state")

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email(recipient_email, otp):
    sender_email = "your_email@aiplabro.com"
    sender_password = "password"
    subject = "Your OTP Code"
    body = f"Your OTP code is {otp}. Please use this to log in."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Debugging: Print the sender email and password to verify they are set
    st.write(f"Debug: SENDER_EMAIL = {sender_email}")
    st.write(f"Debug: SENDER_PASSWORD = {sender_password}")
    try:

        server = smtplib.SMTP('smtp.gmail.com', 587)  # Placeholder for aiplabro.com SMTP server   
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail("exe.it@aiplabro.com", recipient_email, text)
        server.quit()
    except Exception as e:
        st.error(f"Failed to send OTP email: {str(e)}")
def read_email_addresses(file_path):
    """Read email addresses from a file and return as a list."""
    try:
        with open(file_path, 'r') as file:
            emails = file.read().splitlines()
        return emails
    except Exception as e:
        st.error(f"Failed to read email addresses: {str(e)}")
        return []

load_dotenv()

def _get_openai_api_key() -> str:
    """Return OPENAI_API_KEY from env or Streamlit secrets.

    - Prefers OS env var
    - Fallback to st.secrets["OPENAI_API_KEY"] when running on Streamlit Cloud
    - Trims accidental surrounding quotes
    """
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        try:
            # Import inside function to avoid issues in non-Streamlit contexts
            import streamlit as _st
            key = _st.secrets.get("OPENAI_API_KEY") if hasattr(_st, "secrets") else None
        except Exception:
            key = None
    if isinstance(key, str):
        key = key.strip().strip('"').strip("'")
    return key or ""

OPENAI_API_KEY = _get_openai_api_key()
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY not found. Set it in environment variables or Streamlit secrets.")
    st.stop()

# OpenAI API key is now handled by the OpenAI client in each function


class DocumentService:
    """Service for document processing and retrieval using OpenAI models."""
    
    def __init__(self, department_manager: 'DepartmentManager'):
        self.department_manager = department_manager
    
    def load_department_db(self, department_name: str):
        """Load department-specific vectorstore"""
        try:
            db = self.department_manager.get_department_index(department_name)
            if not db:
                st.error(f"No index found for department: {department_name}")
                return None, None
            return db
        except Exception as e:
            st.error(f"Error loading index for department {department_name}: {str(e)}")
            return None
    
    def get_department_index(self, department_name):
        return self.department_manager.get_department_index(department_name)

    def get_embeddings(self, texts: list):
        """Generate embeddings using text-embedding-3-large model."""
        try:
            from openai import OpenAI
            client = OpenAI()
            response = client.embeddings.create(
                input=texts,
                model=config.EMBEDDING_MODEL
            )
            return [embedding for embedding in response.data[0].embedding] if response.data else []
        except Exception as e:
            st.error(f"OpenAI Embedding error: {str(e)}")
            return []
    
    def generate_text(self, prompt: str, temperature=0.3) -> str:
        """Generate text using GPT-4 Omni (multimodel-gpt-4o)."""
        try:
            from openai import OpenAI
            client = OpenAI()
            response = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"OpenAI Chat error: {str(e)}")
            return ""

    def get_department_docs(self, department_name):
        return self.department_manager.get_department_docs(department_name)


SUGGESTIONS = {
    "HR": [
        "What is the leave policy?",
        "How do I apply for leave?",
        "What are the company holidays?"
    ],
    "Accounts": [
        "How do I claim expenses?",
        "What is the reimbursement process?",
        "How to get my salary slip?"
    ],
    "Sales": [
        "What is the sales target for this month?",
        "How to update a lead status?",
        "What is the commission structure?"
    ],
    "Marketing": [
        "What campaigns are running this quarter?",
        "How to request marketing materials?",
        "Who is the marketing head?"
    ],
    "IT": [
        "How to reset my password?",
        "How to request new hardware?",
        "What is the IT support contact?"
    ],
    "Operations": [
        "What is the office timing?",
        "How to book a meeting room?",
        "Who manages facility issues?"
    ]
}


# --- Dynamic Greeting Function ---
def get_greeting():
    from datetime import datetime
    # Use local timezone; default to Asia/Kolkata, override with APP_TIMEZONE env
    try:
        local_tz_name = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
        local_tz = pytz.timezone(local_tz_name)
        hour = datetime.now(local_tz).hour
    except Exception:
        # Fallback to naive local time if timezone not available
        hour = datetime.now().hour
    if hour < 12:
        return "Good morning!"
    elif hour < 18:
        return "Good afternoon!"
    else:
        return "Good evening!"

# --- Custom CSS for Dark Theme Only ---
st.markdown(
    """
    <style>
    /* Force dark theme globally */
    .stApp {
        color-scheme: dark !important;
        background: linear-gradient(135deg, #1e1e2f, #0f2027) !important;
    }
    
    body {
        background: linear-gradient(135deg, #1e1e2f, #0f2027) !important;
        color: #ffffff !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    
    .main .block-container {
        background: transparent !important;
    }
    
    /* Override Streamlit's theme detection */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #1e1e2f, #0f2027) !important;
    }
    
    /* Force dark theme for all components */
    .stSelectbox > div > div {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    .stTextInput > div > div > input {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    /* Force white text for all content */
    .stMarkdown, .stMarkdown p, .stMarkdown div {
        color: #ffffff !important;
    }
    
    /* Chat history text in white */
    .query-text, .answer-text {
        color: #ffffff !important;
    }
    
    /* All text elements in white */
    p, div, span, h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
    }
    div[data-testid="stSelectbox"] > label {
        background-color: #34495e !important;
        color: #ecf0f1 !important;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
    }
    .stButton>button {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        font-size: 16px !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1) !important;
        outline: none !important;
    }
    .stButton>button:hover {
        background-color: #1d4ed8 !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
        transform: translateY(-1px) !important;
    }
    .stButton>button:active, .stButton>button:focus {
        background-color: #1e40af !important;
        color: #ffffff !important;
        border: none !important;
        outline: none !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2) !important;
        transform: translateY(1px) !important;
    }
    .stTextInput>div>input {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        font-size: 16px !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1) !important;
    }
    .stTextInput>div>input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3) !important;
        outline: none !important;
    }
    .stTextInput>div>input::placeholder {
        color: #94a3b8 !important;
        opacity: 1 !important;
    }
    @media (prefers-color-scheme: dark) {
        .stTextInput>div>input, .stButton>button, div[data-testid="stSelectbox"] > label, .stTextInput>div>input, .stButton>button, div[data-testid="stSelectbox"] > label {
            color: #ffffff;
        }
        div[style*="color: #000000;"] {
            color: #ffffff !important;
        }
        .query-text, .answer-text {
            color: #ffffff !important;
        }
    }
    @media (prefers-color-scheme: light) {
        .query-text, .answer-text {
            color: #000000 !important;
        }
    }
    """,
    unsafe_allow_html=True
)

def main():
    st.set_page_config(
        page_title="AIPL Mind", 
        layout="centered",
        initial_sidebar_state="expanded"
    )
    
    # Force dark theme and hide theme menu
    st.markdown("""
    <style>
    .stApp {
        color-scheme: dark !important;
    }
    .stApp > header {
        background-color: transparent;
    }
    .stApp > div {
        background-color: #0f172a;
    }
    
    /* Hide Streamlit's theme menu */
    .stApp > div[data-testid="stToolbar"] {
        display: none !important;
    }
    
    /* Hide hamburger menu that contains theme options */
    .stApp > div[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Force dark theme on all elements */
    * {
        color-scheme: dark !important;
    }
    
    /* Ensure all Streamlit text is white */
    .stMarkdown, .stMarkdown p, .stMarkdown div, .stMarkdown span {
        color: #ffffff !important;
    }
    
    /* Streamlit content areas */
    .main .block-container {
        color: #ffffff !important;
    }
    
    /* All text in main content */
    .main .block-container p, .main .block-container div, .main .block-container span {
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'email' not in st.session_state:
        st.session_state.email = ""
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    if 'selected_department' not in st.session_state:
        st.session_state.selected_department = ""

    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'email' not in st.session_state:
        st.session_state.email = ""
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""

    # User login with email domain check
    if not st.session_state.logged_in:
        st.title("🔐 Login to AIPL Chatbot")
        
        # Create a form for login
        with st.form("login_form"):
            st.markdown("### 👤 User Information")
            user_name = st.text_input("Enter your full name", placeholder="e.g., John Doe")
            email = st.text_input("Enter your company email", placeholder="e.g., john.doe@aiplabro.com")
            password = st.text_input("Enter password", type="password")
            
            submitted = st.form_submit_button("🔑 Login", use_container_width=True)
            
            if submitted:
                # Validate inputs
                if not user_name.strip():
                    st.error("Please enter your full name.")
                elif not email.strip():
                    st.error("Please enter your email address.")
                elif not password.strip():
                    st.error("Please enter your password.")
                else:
                    # Allow only company emails
                    if re.match(r"^[\w\.-]+@(aiplabro\.com|ajitindustries\.com)$", email) and password == "password":
                        st.session_state.logged_in = True
                        st.session_state.email = email
                        st.session_state.user_name = user_name.strip()
                        st.session_state.login_time = datetime.now().isoformat()
                        
                        # Log successful login
                        user_logger.log_user_login(email, True, user_name.strip())
                        
                        st.success(f"Welcome {user_name}! Logged in successfully!")
                        st.rerun()
                    else:
                        # Log failed login attempt
                        user_logger.log_user_login(email, False, "")
                        st.error("Invalid email or password. Only @aiplabro.com and @ajitindustries.com emails allowed.")
        return

    with st.sidebar:
        # User info and logout
        st.markdown(f"<div style='background: linear-gradient(135deg, #059669, #10b981); color: white; padding: 15px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 6px 20px rgba(0,0,0,0.15); border: 1px solid rgba(16, 185, 129, 0.3);'><h3 style='margin:0; text-align:center; font-size: 1.2rem;'>👤 {st.session_state.user_name}</h3><p style='margin:5px 0 0 0; text-align:center; font-size: 0.9rem; opacity: 0.8;'>{st.session_state.email}</p></div>", unsafe_allow_html=True)
        
        # Add refresh button for documents
        if st.button("🔄 Refresh Documents", help="Click to reload documents from admin panel"):
            # Clear all document session states
            for dept in ["HR", "Accounts", "Sales", "IT", "Operations"]:
                session_key = f"docs_{dept.lower()}"
                if session_key in st.session_state:
                    del st.session_state[session_key]
            st.success("Documents refreshed! Please check the status below.")
            st.rerun()
        
        # Add department status info
        st.markdown("---")
        st.markdown("**📊 Department Status:**")
        for dept in ["HR", "Accounts", "Sales", "IT", "Operations"]:
            try:
                docs = get_department_docs_from_session(dept)
                status = "✅" if docs else "❌"
                st.markdown(f"{status} **{dept}**: {len(docs)} documents")
            except:
                st.markdown(f"❓ **{dept}**: Status unknown")
        
        if st.button("🚪 Logout", key="logout_btn"):
            # Log logout
            user_logger.log_user_logout(st.session_state.email)
            # Clear session
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.markdown("<div style='background: linear-gradient(135deg, #0369a1, #0ea5e9); color: white; padding: 18px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 6px 20px rgba(0,0,0,0.15); border: 1px solid rgba(14, 165, 233, 0.3);'><h2 style='margin:0; text-align:center; font-size: 1.5rem; letter-spacing: 1px; font-weight: 600;'>🌐 Select Response Language</h2></div>", unsafe_allow_html=True)
        language_options = config.LANGUAGE_OPTIONS
        language = st.selectbox("Language", list(language_options.keys()))
        language_code = language_options[language]

        st.markdown("<div style='background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 18px; border-radius: 12px; margin: 25px 0; box-shadow: 0 6px 20px rgba(0,0,0,0.15); border: 1px solid rgba(59, 130, 246, 0.3);'><h2 style='margin:0; text-align:center; font-size: 1.5rem; letter-spacing: 1px; font-weight: 600;'>🏢 Select Department</h2></div>", unsafe_allow_html=True)
        departments = config.DEPARTMENTS
        department = st.selectbox("Department", ["Select..."] + departments)

        st.markdown("<div style='background: linear-gradient(135deg, #4f46e5, #8b5cf6); color: white; padding: 18px; border-radius: 12px; margin: 25px 0; box-shadow: 0 6px 20px rgba(0,0,0,0.15); border: 1px solid rgba(139, 92, 246, 0.3);'><h2 style='margin:0; text-align:center; font-size: 1.5rem; letter-spacing: 1px; font-weight: 600;'>💡 Suggestions</h2></div>", unsafe_allow_html=True)
        if department in SUGGESTIONS:
            for s in SUGGESTIONS[department]:
                st.markdown(f"<div style='background: rgba(79, 70, 229, 0.1); padding: 12px 16px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #8b5cf6; font-size: 0.95rem; color: #f1f5f9; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: all 0.2s ease-in-out;'>{s}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align: center; color: #94a3b8; padding: 16px; background: rgba(30, 41, 59, 0.4); border-radius: 8px; margin: 10px 0; border: 1px dashed rgba(148, 163, 184, 0.3);'>Please select a department to view suggestions</div>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: auto; background: linear-gradient(135deg, #0f172a, #1e293b); padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.25); border: 1px solid rgba(59, 130, 246, 0.2);'>
            <h1 style='color: #f8fafc; font-size: 2.8rem; margin-bottom: 0.5em; font-weight: 700; letter-spacing: 1px; text-shadow: 0 2px 4px rgba(0,0,0,0.2);'>Welcome to AIPL Chatbot</h1>
            <div style='color: #fbbf24; font-weight: 600; font-size: 1.2rem; background: rgba(251, 191, 36, 0.1); padding: 8px 16px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>{get_greeting()}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    placeholder = "Ask a question..."
    if department == "Select...":
        st.markdown("""<div style='background: rgba(56, 189, 248, 0.1); color: #38bdf8; padding: 16px; border-radius: 8px; margin: 16px 0; border-left: 4px solid #38bdf8; font-size: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'><strong>ℹ️ Info:</strong> Please select a department to ask a question.</div>""", unsafe_allow_html=True)
    else:
        # Check if department has documents using session state
        try:
            docs = get_department_docs_from_session(department)
            
            # Debug information
            st.markdown(f"""<div style='background: rgba(100, 100, 100, 0.1); color: #666; padding: 8px; border-radius: 4px; margin: 8px 0; font-size: 0.8rem;'><strong>Debug:</strong> Found {len(docs)} documents for {department} department</div>""", unsafe_allow_html=True)
            
            if not docs:
                st.markdown(f"""<div style='background: rgba(251, 191, 36, 0.1); color: #fbbf24; padding: 16px; border-radius: 8px; margin: 16px 0; border-left: 4px solid #fbbf24; font-size: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'><strong>⚠️ Notice:</strong> No documents found for {department} department. Please upload documents via admin panel first.</div>""", unsafe_allow_html=True)
                placeholder = f"Ask a question from {department} (no documents uploaded yet)..."
            else:
                st.markdown(f"""<div style='background: rgba(34, 197, 94, 0.1); color: #22c55e; padding: 16px; border-radius: 8px; margin: 16px 0; border-left: 4px solid #22c55e; font-size: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'><strong>✅ Ready:</strong> {len(docs)} documents loaded for {department} department. You can ask questions now!</div>""", unsafe_allow_html=True)
                placeholder = f"Ask a question from {department}..."
        except Exception as e:
            st.markdown(f"""<div style='background: rgba(239, 68, 68, 0.1); color: #ef4444; padding: 16px; border-radius: 8px; margin: 16px 0; border-left: 4px solid #ef4444; font-size: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'><strong>❌ Error:</strong> Could not check documents for {department} department. Error: {str(e)}</div>""", unsafe_allow_html=True)
            placeholder = f"Ask a question from {department}..."

    # Display chat history before the input box
    if st.session_state.query_history:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 18px; border-radius: 12px; margin: 25px 0; box-shadow: 0 6px 20px rgba(0,0,0,0.2); border: 1px solid rgba(59, 130, 246, 0.3);'>
            <h2 style='margin:0; text-align:center; font-size: 1.6rem; letter-spacing: 1px; font-weight: 600;'>AIPL Chat History</h2>
        </div>
        """, unsafe_allow_html=True)
        for q, r in st.session_state.query_history:
            st.markdown(f"""
            <div style='background: rgba(30, 41, 59, 0.4); padding: 20px; border-radius: 12px; margin: 16px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.15); border: 1px solid rgba(59, 130, 246, 0.2);'>
                <div class='query-text' style='margin-bottom: 14px; color: #ffffff; font-size: 16px;'><strong style='color: #60a5fa;'>You:</strong> {q}</div>
                <div class='answer-text' style='color: #ffffff; font-size: 16px; line-height: 1.6;'><strong style='color: #38bdf8;'>AIPL Bot:</strong> {r}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Initialize the query state if not already present
    if 'current_query' not in st.session_state:
        st.session_state.current_query = ""
    
    # Define callback function to process query and clear input
    def process_query():
        user_query = st.session_state.bottom_user_query
        if not user_query:
            return
        
        # Log user question
        user_logger.log_user_question(
            email=st.session_state.email,
            question=user_query,
            department=department,
            language=language
        )
        
        start_time = datetime.now()
        
        try:
            # Use cached department manager
            department_manager = get_department_manager()
            
            # Initialize services with cached manager
            if 'document_service' not in st.session_state:
                st.session_state.document_service = DocumentService(department_manager)
            if 'query_processor' not in st.session_state:
                st.session_state.query_processor = QueryProcessor(department_manager)
            
            document_service = st.session_state.document_service
            query_processor = st.session_state.query_processor
            
            # Check if department documents exist using session state
            docs = get_department_docs_from_session(department)
            if not docs:
                response = f"❌ No documents found for {department} department. Please upload documents via admin."
                
                # Calculate response time for error
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                
                # Log the response
                user_logger.log_bot_response(
                    email=st.session_state.email,
                    question=user_query,
                    response=response,
                    success=False,
                    response_time=response_time
                )
                
                st.session_state.query_history.append((user_query, response))
                st.session_state.bottom_user_query = ""
                return
                
            # Check if department index exists
            faiss_index = department_manager.get_department_index(department)
            if faiss_index is None:
                response = f"❌ No index found for {department} department. Please rebuild the index via admin."
                
                # Calculate response time for error
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                
                # Log the response
                user_logger.log_bot_response(
                    email=st.session_state.email,
                    question=user_query,
                    response=response,
                    success=False,
                    response_time=response_time
                )
                
                st.session_state.query_history.append((user_query, response))
                st.session_state.bottom_user_query = ""
                return
            
            # Process the query
            with st.spinner("🤖 Generating response..."):
                questions = re.split(r'[?.!]', user_query)
                responses = []
                
                for question in questions:
                    if question.strip():
                        try:
                            response = query_processor.process_query(question.strip(), department, language_code=language_code)
                            responses.append(response)
                        except Exception as e:
                            error_response = f"❌ Error processing question: {str(e)}"
                            responses.append(error_response)
                
                response = " ".join(responses) if responses else "❌ No response generated. Please try again."
                
                # Calculate response time
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                
                # Log successful response
                user_logger.log_bot_response(
                    email=st.session_state.email,
                    question=user_query,
                    response=response,
                    success=True,
                    response_time=response_time
                )
                
        except Exception as e:
            response = f"\u274C Error: {str(e)}"
            import traceback
            st.error(traceback.format_exc())
            
            # Calculate response time for error
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # Log error
            user_logger.log_error(
                email=st.session_state.email,
                error_type="Query Processing Error",
                error_message=str(e)
            )
            
            # Log failed response
            user_logger.log_bot_response(
                email=st.session_state.email,
                question=user_query,
                response=response,
                success=False,
                response_time=response_time
            )
        
        # Add to history
        st.session_state.query_history.append((user_query, response))
        # Clear the query state
        st.session_state.bottom_user_query = ""
        # Force UI refresh
        st.rerun()
    
    # Fixed input box at the bottom with improved styling
    st.markdown("<div class='chat-input-container'>", unsafe_allow_html=True)
    
    # Use form with clear_on_submit for automatic input clearing
    with st.form(key="query_form", clear_on_submit=True):
        user_input = st.text_input(placeholder, disabled=(department == "Select..."))
        submit_button = st.form_submit_button("Submit", disabled=(department == "Select..."))
        
        if submit_button and user_input:
            st.session_state.bottom_user_query = user_input
            process_query()
    
    # Auto-scroll to the bottom
    st.markdown("<script>window.scrollTo(0, document.body.scrollHeight);</script>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Add CSS for fixed input box at bottom
    st.markdown("""
    <style>
    .chat-input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: rgba(30, 41, 59, 0.98) !important;
        padding: 20px;
        box-shadow: 0 -5px 15px rgba(0, 0, 0, 0.4) !important;
        z-index: 1000;
        border-top: 1px solid rgba(52, 152, 219, 0.4) !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        transition: none !important;
    }
    
    /* Add padding at the bottom of the page to prevent content from being hidden behind the fixed input */
    .main .block-container {
        padding-bottom: 100px;
    }
    
    /* Auto-scroll to bottom script */
    </style>
    <script>
    // Function to scroll to bottom of page
    function scrollToBottom() {
        window.scrollTo(0, document.body.scrollHeight);
    }
    
    // Scroll when page loads
    window.onload = scrollToBottom;
    
    // Scroll when new content is added
    const observer = new MutationObserver(scrollToBottom);
    observer.observe(document.body, { childList: true, subtree: true });
    </script>
    """, unsafe_allow_html=True)

    # Session state initialization for selected department
    if 'selected_department' not in st.session_state:
        st.session_state.selected_department = department

    # Handle department change
    if department != "Select..." and st.session_state.selected_department != department:
        st.session_state.selected_department = department
        # When department changes, we don't need to process any query
        # Just update the session state and continue
        pass


if __name__ == "__main__":
    main()



# Call the function to send OTPs
# send_otps_to_all()
