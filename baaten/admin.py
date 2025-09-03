import streamlit as st
from pathlib import Path
from department_manager import DepartmentManager
import openai
import PyPDF2
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from utils.user_logger import user_logger
load_dotenv()

st.set_page_config(page_title="Admin - Department Data Upload", layout="wide")

# Force dark theme for admin portal
st.markdown("""
<style>
.stApp {
    color-scheme: dark !important;
    background: linear-gradient(135deg, #1e1e2f, #0f2027) !important;
}
body {
    background: linear-gradient(135deg, #1e1e2f, #0f2027) !important;
    color: #ffffff !important;
}
.main .block-container {
    background: transparent !important;
}
/* Force white text for all content */
.stMarkdown, .stMarkdown p, .stMarkdown div, .stMarkdown span {
    color: #ffffff !important;
}
/* All text elements in white */
p, div, span, h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

def _get_openai_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        try:
            key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
        except Exception:
            key = None
    if isinstance(key, str):
        key = key.strip().strip('"').strip("'")
    return key or ""

# Try to get the API key from secrets or environment
api_key = _get_openai_api_key()
if not api_key:
    st.error("OPENAI_API_KEY not set in environment or Streamlit secrets.")
    st.stop()

# OpenAI API key is now handled by the OpenAI client in each function

# Initialize DepartmentManager
department_manager = DepartmentManager()

def clean_csv_files():
    """Clean up old CSV files that might have formatting issues"""
    logs_dir = "user_logs"
    if not os.path.exists(logs_dir):
        return
    
    for filename in ["logins.csv", "questions.csv", "responses.csv", "errors.csv"]:
        filepath = os.path.join(logs_dir, filename)
        if os.path.exists(filepath):
            try:
                # Try to read the file
                df = pd.read_csv(filepath)
                # If successful, check if we need to add user_name column
                if filename == "logins.csv" and 'user_name' not in df.columns:
                    df['user_name'] = ''
                    df.to_csv(filepath, index=False)
                    st.info(f"✅ Added user_name column to {filename}")
            except Exception as e:
                # If file is corrupted, try to fix it
                try:
                    # Read with error handling (modern pandas syntax)
                    df = pd.read_csv(filepath, on_bad_lines='skip')
                    if not df.empty:
                        # Add missing columns if needed
                        if filename == "logins.csv" and 'user_name' not in df.columns:
                            df['user_name'] = ''
                        # Save the cleaned file
                        df.to_csv(filepath, index=False)
                        st.success(f"✅ Fixed and cleaned {filename}")
                    else:
                        # If file is completely corrupted, remove it
                        os.remove(filepath)
                        st.warning(f"⚠️ Removed corrupted {filename}")
                except Exception as e2:
                    st.error(f"❌ Could not fix {filename}: {str(e2)}")

def load_csv_data(filename):
    """Load data from CSV file with error handling for column mismatches"""
    filepath = os.path.join("user_logs", filename)
    if os.path.exists(filepath):
        try:
            # Try to read with default settings
            return pd.read_csv(filepath)
        except pd.errors.ParserError as e:
            # If there's a column mismatch, try to read with error handling
            try:
                # Read with error handling for bad lines (modern pandas syntax)
                df = pd.read_csv(filepath, on_bad_lines='skip')
                st.warning(f"⚠️ Some data rows in {filename} had formatting issues and were skipped.")
                return df
            except Exception as e2:
                st.error(f"❌ Error reading {filename}: {str(e2)}")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Error reading {filename}: {str(e)}")
            return pd.DataFrame()
    return pd.DataFrame()

def show_logs_dashboard():
    """Display the logs dashboard"""
    # Clean up any corrupted CSV files first
    clean_csv_files()
    
    st.title("📊 User Activity Dashboard")
    st.markdown("---")
    
    # Additional dark theme CSS for logs dashboard
    st.markdown("""
    <style>
    /* Force dark theme for logs dashboard specifically */
    .stDataFrame {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    .stDataFrame table {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    .stDataFrame th {
        background-color: #374151 !important;
        color: #ffffff !important;
    }
    
    .stDataFrame td {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    /* Dark theme for selectbox in sidebar */
    .stSelectbox > div > div {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    /* Dark theme for date input */
    .stDateInput > div > div > input {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    /* Dark theme for buttons */
    .stButton > button {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: none !important;
    }
    
    .stButton > button:hover {
        background-color: #1d4ed8 !important;
    }
    
    /* Dark theme for tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e293b !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #374151 !important;
        color: #ffffff !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }
    
    /* Dark theme for metrics */
    [data-testid="metric-container"] {
        background-color: #1e293b !important;
        border: 1px solid #374151 !important;
    }
    
    [data-testid="metric-container"] > div {
        color: #ffffff !important;
    }
    
    /* Dark theme for info boxes */
    .stAlert {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #374151 !important;
    }
    
    /* Dark theme for JSON display */
    .stJson {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    /* Dark theme for download button */
    .stDownloadButton > button {
        background-color: #059669 !important;
        color: #ffffff !important;
        border: none !important;
    }
    
    .stDownloadButton > button:hover {
        background-color: #047857 !important;
    }
    
    /* Dark theme for sidebar */
    .css-1d391kg {
        background-color: #1e293b !important;
    }
    
    /* Dark theme for headers */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #ffffff !important;
    }
    
    /* Dark theme for data tables */
    .dataframe {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    .dataframe th {
        background-color: #374151 !important;
        color: #ffffff !important;
    }
    
    .dataframe td {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    /* Fix white text visibility issues */
    .stSelectbox label {
        color: #ffffff !important;
    }
    
    .stSelectbox > div > div > div {
        color: #ffffff !important;
    }
    
    /* Fix dropdown text visibility */
    .stSelectbox [data-baseweb="select"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    .stSelectbox [data-baseweb="select"] > div {
        color: #ffffff !important;
    }
    
    /* Fix date input text */
    .stDateInput label {
        color: #ffffff !important;
    }
    
    .stDateInput > div > div > input {
        color: #ffffff !important;
    }
    
    /* Fix all text in sidebar */
    .css-1d391kg * {
        color: #ffffff !important;
    }
    
    /* Fix selectbox dropdown options */
    [data-baseweb="menu"] {
        background-color: #1e293b !important;
    }
    
    [data-baseweb="menu"] li {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    [data-baseweb="menu"] li:hover {
        background-color: #374151 !important;
        color: #ffffff !important;
    }
    
    /* Force all text to be white */
    .stSelectbox, .stSelectbox *, .stDateInput, .stDateInput * {
        color: #ffffff !important;
    }
    
    /* Fix info boxes text */
    .stInfo, .stWarning, .stError, .stSuccess {
        color: #ffffff !important;
    }
    
    .stInfo > div, .stWarning > div, .stError > div, .stSuccess > div {
        color: #ffffff !important;
    }
    
    /* Additional fixes for text visibility */
    .stSelectbox [data-baseweb="select"] span {
        color: #ffffff !important;
    }
    
    /* Fix dropdown arrow */
    .stSelectbox [data-baseweb="select"] svg {
        fill: #ffffff !important;
    }
    
    /* Fix all text in the entire app */
    .stApp * {
        color: #ffffff !important;
    }
    
    /* Override any white backgrounds that might be hiding text */
    .stSelectbox [data-baseweb="select"] {
        background-color: #1e293b !important;
        border-color: #374151 !important;
    }
    
    /* Fix date picker */
    .stDateInput [data-baseweb="datepicker"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    /* Ensure all labels are white */
    label {
        color: #ffffff !important;
    }
    
    /* Fix any remaining text visibility issues */
    .stSelectbox div, .stDateInput div, .stTextInput div {
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar for filters
    with st.sidebar:
        st.header("🔍 Filters")
        
        # Date filter
        date_filter = st.date_input(
            "Select Date",
            value=datetime.now().date(),
            max_value=datetime.now().date()
        )
        
        # User filter
        all_users = set()
        user_display_names = {}
        
        for filename in ["logins.csv", "questions.csv", "responses.csv"]:
            df = load_csv_data(filename)
            if not df.empty and 'email' in df.columns:
                for _, row in df.iterrows():
                    email = row['email']
                    user_name = row.get('user_name', '')
                    if user_name and user_name != 'N/A':
                        user_display_names[email] = user_name
                    all_users.add(email)
        
        # Create user options with names when available
        user_options = ["All Users"]
        for email in sorted(all_users):
            if email in user_display_names:
                user_options.append(f"{user_display_names[email]} ({email})")
            else:
                user_options.append(email)
        
        selected_user = st.selectbox(
            "Select User",
            user_options
        )
        
        # Extract email from selected user option
        if selected_user != "All Users":
            if "(" in selected_user and ")" in selected_user:
                # Format: "John Doe (john@email.com)"
                selected_user = selected_user.split("(")[1].split(")")[0]
            # If no parentheses, selected_user is already the email
        
        # Event type filter
        event_types = ["All Events", "LOGIN", "QUESTION", "RESPONSE", "LOGOUT", "ERROR"]
        selected_event = st.selectbox("Event Type", event_types)
    
    # Main dashboard content
    col1, col2, col3, col4 = st.columns(4)
    
    # Load all data
    logins_df = load_csv_data("logins.csv")
    questions_df = load_csv_data("questions.csv")
    responses_df = load_csv_data("responses.csv")
    errors_df = load_csv_data("errors.csv")
    
    # Filter data by date
    if not logins_df.empty:
        logins_df['timestamp'] = pd.to_datetime(logins_df['timestamp'])
        logins_df = logins_df[logins_df['timestamp'].dt.date == date_filter]
    
    if not questions_df.empty:
        questions_df['timestamp'] = pd.to_datetime(questions_df['timestamp'])
        questions_df = questions_df[questions_df['timestamp'].dt.date == date_filter]
    
    if not responses_df.empty:
        responses_df['timestamp'] = pd.to_datetime(responses_df['timestamp'])
        responses_df = responses_df[responses_df['timestamp'].dt.date == date_filter]
    
    if not errors_df.empty:
        errors_df['timestamp'] = pd.to_datetime(errors_df['timestamp'])
        errors_df = errors_df[errors_df['timestamp'].dt.date == date_filter]
    
    # Filter by user
    if selected_user != "All Users":
        if not logins_df.empty:
            logins_df = logins_df[logins_df['email'] == selected_user]
        if not questions_df.empty:
            questions_df = questions_df[questions_df['email'] == selected_user]
        if not responses_df.empty:
            responses_df = responses_df[responses_df['email'] == selected_user]
        if not errors_df.empty:
            errors_df = errors_df[errors_df['email'] == selected_user]
    
    # Key metrics
    with col1:
        st.metric(
            label="Total Logins",
            value=len(logins_df) if not logins_df.empty else 0
        )
    
    with col2:
        st.metric(
            label="Total Questions",
            value=len(questions_df) if not questions_df.empty else 0
        )
    
    with col3:
        st.metric(
            label="Total Responses",
            value=len(responses_df) if not responses_df.empty else 0
        )
    
    with col4:
        success_rate = 0
        if not responses_df.empty and 'success' in responses_df.columns:
            success_count = len(responses_df[responses_df['success'] == True])
            success_rate = (success_count / len(responses_df)) * 100
        
        st.metric(
            label="Success Rate",
            value=f"{success_rate:.1f}%"
        )
    
    st.markdown("---")
    
    # Detailed views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 All Activities", 
        "🔐 Logins", 
        "❓ Questions", 
        "🤖 Responses", 
        "❌ Errors"
    ])
    
    with tab1:
        st.subheader("📋 All Activities")
        
        # Combine all activities
        all_activities = []
        
        if not logins_df.empty:
            for _, row in logins_df.iterrows():
                # Get user name if available, otherwise use email
                user_display = row.get('user_name', 'N/A') if row.get('user_name') else row['email']
                all_activities.append({
                    'timestamp': row['timestamp'],
                    'event_type': 'LOGIN',
                    'user': user_display,
                    'email': row['email'],
                    'details': f"Success: {row.get('success', 'N/A')}",
                    'ip_address': row.get('ip_address', 'N/A')
                })
        
        if not questions_df.empty:
            for _, row in questions_df.iterrows():
                # Try to get user name from logins data
                user_display = user_display_names.get(row['email'], row['email'])
                all_activities.append({
                    'timestamp': row['timestamp'],
                    'event_type': 'QUESTION',
                    'user': user_display,
                    'email': row['email'],
                    'details': f"Dept: {row.get('department', 'N/A')}, Lang: {row.get('language', 'N/A')}",
                    'question': row.get('question', 'N/A')[:100] + "..." if len(str(row.get('question', ''))) > 100 else row.get('question', 'N/A')
                })
        
        if not responses_df.empty:
            for _, row in responses_df.iterrows():
                # Try to get user name from logins data
                user_display = user_display_names.get(row['email'], row['email'])
                all_activities.append({
                    'timestamp': row['timestamp'],
                    'event_type': 'RESPONSE',
                    'user': user_display,
                    'email': row['email'],
                    'details': f"Success: {row.get('success', 'N/A')}, Time: {row.get('response_time_seconds', 'N/A')}s",
                    'response': row.get('response', 'N/A')[:100] + "..." if len(str(row.get('response', ''))) > 100 else row.get('response', 'N/A')
                })
        
        if all_activities:
            activities_df = pd.DataFrame(all_activities)
            activities_df = activities_df.sort_values('timestamp', ascending=False)
            st.dataframe(activities_df, use_container_width=True)
        else:
            st.info("No activities found for the selected filters.")
    
    with tab2:
        st.subheader("🔐 Login Activities")
        if not logins_df.empty:
            st.dataframe(logins_df, use_container_width=True)
        else:
            st.info("No login activities found.")
    
    with tab3:
        st.subheader("❓ Questions Asked")
        if not questions_df.empty:
            st.dataframe(questions_df, use_container_width=True)
        else:
            st.info("No questions found.")
    
    with tab4:
        st.subheader("🤖 Bot Responses")
        if not responses_df.empty:
            st.dataframe(responses_df, use_container_width=True)
        else:
            st.info("No responses found.")
    
    with tab5:
        st.subheader("❌ Errors")
        if not errors_df.empty:
            st.dataframe(errors_df, use_container_width=True)
        else:
            st.info("No errors found.")
    
    # User statistics
    st.markdown("---")
    st.subheader("👥 User Statistics")
    
    if selected_user != "All Users":
        # Individual user stats
        user_stats = user_logger.get_user_stats(selected_user)
        
        # Get user display name
        user_display_name = user_display_names.get(selected_user, selected_user)
        st.subheader(f"📊 Statistics for: {user_display_name}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Logins", user_stats['total_logins'])
            st.metric("Total Questions", user_stats['total_questions'])
        with col2:
            st.metric("Total Responses", user_stats['total_responses'])
            st.metric("Successful Responses", user_stats['successful_responses'])
        with col3:
            st.metric("Departments Used", len(user_stats['departments_used']))
            st.metric("Languages Used", len(user_stats['languages_used']))
        
        if user_stats['departments_used']:
            st.write("**Departments Used:**", ", ".join(user_stats['departments_used']))
        if user_stats['languages_used']:
            st.write("**Languages Used:**", ", ".join(user_stats['languages_used']))
    else:
        # Overall statistics
        st.info("Select a specific user to view detailed statistics.")
    
    # Export functionality
    st.markdown("---")
    st.subheader("📤 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export All Logs as CSV"):
            # Create a combined CSV
            all_data = []
            for filename in ["logins.csv", "questions.csv", "responses.csv", "errors.csv"]:
                df = load_csv_data(filename)
                if not df.empty:
                    all_data.append(df)
            
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                csv = combined_df.to_csv(index=False)
                st.download_button(
                    label="Download Combined Logs",
                    data=csv,
                    file_name=f"aipl_logs_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    with col2:
        if st.button("Generate Daily Report"):
            report = user_logger.get_daily_report(date_filter.strftime("%Y-%m-%d"))
            st.json(report)

# Main admin interface
st.title("🗂️ AIPL Admin Portal")
st.write("Welcome to the Admin Portal. Select an option below.")

# Create tabs for different admin functions
tab1, tab2 = st.tabs(["📁 Document Management", "📊 User Activity Logs"])

with tab1:
    st.subheader("📁 Department Data Upload & Indexing")
    st.write("Upload and manage department documents.")

departments = ["HR", "Accounts", "Sales", "IT", "Operations"]  # Add your departments here
department = st.selectbox("Select Department", ["Select..."] + departments)

uploaded_files = st.file_uploader(
    "Upload department documents (PDF only)",
    type=["pdf"],
    accept_multiple_files=True
)

if department != "Select..." and uploaded_files:
    st.info(f"Preparing to index {len(uploaded_files)} files for {department} department.")

    documents = []
    for file in uploaded_files:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        documents.append(text)
        # Save each PDF as a separate file for persistence and per-file management
        department_manager.save_department_pdf(department, file.name, text)

    if st.button("Create Department Index"):
        with st.spinner("Generating embeddings and creating index..."):
            department_manager.create_department_index(department, documents)
            st.success(f"Index created for {department} department! 🎉")
else:
    st.warning("Please select a department and upload at least one PDF file.")

# --- Show uploaded PDFs and delete options ---
if department != "Select...":
    st.subheader(f"Uploaded PDFs for {department} department")
    pdf_files = department_manager.list_department_pdfs(department)
    if pdf_files:
        for pdf_file in pdf_files:
            col1, col2 = st.columns([6,1])
            with col1:
                st.write(pdf_file)
            with col2:
                delete_key = f"delete_{department}_{pdf_file}"
                if st.button("Delete", key=delete_key):
                    st.session_state["pdf_to_delete"] = (department, pdf_file)
                    st.session_state["show_confirm"] = True
    else:
        st.info("No PDFs uploaded for this department.")

# --- Confirmation popup ---
if st.session_state.get("show_confirm", False):
    pdf_to_delete = st.session_state.get("pdf_to_delete")
    if pdf_to_delete:
        department, pdf_file = pdf_to_delete
        st.warning(f"Are you sure you want to delete '{pdf_file}' from {department} department?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Yes, Delete", key="yes_delete"):
                department_manager.delete_department_pdf(department, pdf_file)
                st.success(f"Deleted '{pdf_file}' from {department} department.")
                st.session_state["show_confirm"] = False
                st.session_state.pop("pdf_to_delete", None)
                st.rerun()
        with col_no:
            if st.button("Cancel", key="cancel_delete"):
                st.session_state["show_confirm"] = False
                st.session_state.pop("pdf_to_delete", None)

with tab2:
    show_logs_dashboard()