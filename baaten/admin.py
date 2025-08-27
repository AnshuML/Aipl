import streamlit as st
from pathlib import Path
from department_manager import DepartmentManager
import openai
import PyPDF2
import os
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Admin - Department Data Upload", layout="wide")

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

openai.api_key = api_key

# Initialize DepartmentManager
department_manager = DepartmentManager()

st.title("🗂️ Department Data Upload & Indexing (Admin)")
st.write("Admin page loaded. Please select a department and upload files.")

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
                st.rerun()