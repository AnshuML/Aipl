# 🚀 AIPL Chatbot Setup Guide

## Prerequisites

- Python 3.8 or higher
- OpenAI API Key
- Internet connection for AI services

## Quick Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd Aipl/baaten
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 4. Run the Application

#### For Admin Panel (Document Management):
```bash
streamlit run admin.py
```

#### For User Interface:
```bash
streamlit run app.py
```

## First Time Setup

### 1. Upload Documents
1. Open admin panel: `streamlit run admin.py`
2. Select a department (HR, Accounts, Sales, etc.)
3. Upload PDF documents for that department
4. Click "Create Department Index"
5. Repeat for all departments

### 2. Test the System
1. Open user interface: `streamlit run app.py`
2. Login with company email (@aiplabro.com or @ajitindustries.com)
3. Select a department and ask questions

## Configuration

### Departments
The system supports these departments by default:
- HR
- Accounts  
- Sales
- IT
- Operations

### Languages
Supports 18+ languages including:
- English, Hindi, Tamil, Telugu, Bengali
- Malayalam, Kannada, Gujarati, Marathi
- And many more...

## Troubleshooting

### Common Issues

1. **OpenAI API Error**
   - Check your API key in `.env` file
   - Ensure you have sufficient API credits
   - Check internet connection

2. **No Documents Found**
   - Upload documents via admin panel first
   - Create department indexes

3. **Slow Performance**
   - Ensure good internet connection
   - Check system resources

### Support
For issues, check the logs in `user_logs/` directory or contact the system administrator.

## Security Notes

- Never commit `.env` files to version control
- User logs are stored locally and not shared
- All sensitive data is properly excluded via `.gitignore`
