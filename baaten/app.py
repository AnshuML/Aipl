import streamlit as st
import os
import re
from query_services import QueryProcessor
from dotenv import load_dotenv
from datetime import datetime
import pytz
import random
from typing import List, Tuple, Optional, Dict, Any
from googletrans import Translator  # Updated for googletrans v2
from rank_bm25 import BM25Okapi
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.retrievers import BM25Retriever
import openai

# Local imports
from config import config
from department_manager import DepartmentManager

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

# Set OpenAI API key for openai module
openai.api_key = OPENAI_API_KEY


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
            response = openai.Embedding.create(
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
            response = openai.ChatCompletion.create(
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
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning!"
    elif hour < 18:
        return "Good afternoon!"
    else:
        return "Good evening!"

# --- Custom CSS for Language Select ---
st.markdown(
    """
    <style>
    body {
        background: linear-gradient(135deg, #1e1e2f, #0f2027) !important;
        color: #ffffff !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    .main .block-container {
        background: transparent !important;
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
    st.set_page_config(page_title="AIPL Mind", layout="centered")

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

    # User login with email domain check
    if not st.session_state.logged_in:
        st.title("🔐 Login to AIPL Chatbot")
        email = st.text_input("Enter your company email", value=st.session_state.email)
        password = st.text_input("Enter password", type="password")
        if st.button("Login"):
            if re.match(r"^[\w\.-]+@aiplabro\.com$", email) and password == "password":
                st.session_state.logged_in = True
                st.session_state.email = email
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid email or password.")
        return

    with st.sidebar:
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
                <div class='query-text' style='margin-bottom: 14px; color: #f1f5f9; font-size: 16px;'><strong style='color: #60a5fa;'>You:</strong> {q}</div>
                <div class='answer-text' style='color: #f8fafc; font-size: 16px; line-height: 1.6;'><strong style='color: #38bdf8;'>AIPL Bot:</strong> {r}</div>
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
        
        # Existing logic for processing the query
        department_manager = DepartmentManager()
        document_service = DocumentService(department_manager)
        query_processor = QueryProcessor(department_manager)
        try:
            # Debug information removed
            
            # Check if department documents exist
            docs = department_manager.get_department_docs(department)
            if not docs:
                response = f"❌ No documents found for {department} department. Please upload documents via admin."
                st.session_state.query_history.append((user_query, response))
                st.session_state.bottom_user_query = ""
                return
                
            # Check if department index exists
            faiss_index = department_manager.get_department_index(department)
            if faiss_index is None:
                response = f"❌ No index found for {department} department. Please rebuild the index via admin."
                st.session_state.query_history.append((user_query, response))
                st.session_state.bottom_user_query = ""
                return
            
            # Process the query
            questions = re.split(r'[?.!]', user_query)
            responses = []
            for question in questions:
                if question.strip():
                    response = query_processor.process_query(question.strip(), department, language_code=language_code)
                    responses.append(response)
            response = " ".join(responses)
        except Exception as e:
            response = f"\u274C Error: {str(e)}"
            import traceback
            st.error(traceback.format_exc())
        
        # Add to history
        st.session_state.query_history.append((user_query, response))
        # Clear the input by setting an empty string in session state
        st.session_state.bottom_user_query = ""
    
    # Fixed input box at the bottom with improved styling
    st.markdown("<div class='chat-input-container'>", unsafe_allow_html=True)
    st.text_input(placeholder, key="bottom_user_query", disabled=(department == "Select..."))
    if st.button("Submit", disabled=(department == "Select..."), on_click=process_query):
        pass
    
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
