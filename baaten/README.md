# 🤖 Multi-Department RAG Chatbot System

## 🎯 Project Overview

Ek robust, scalable, aur intelligent RAG (Retrieval-Augmented Generation) chatbot system jo har department ke liye alag-alag data handle karta hai aur 10 seconds ke andar accurate responses deta hai.

### ✨ Key Features

- **🏢 Multi-Department Support**: HR, Accounts, Sales, Marketing, IT, Operations, Customer Support
- **🌐 Multi-Language Support**: 18+ languages including Hindi, Tamil, Telugu, Bengali, etc.
- **⚡ Fast Response**: Sub-10 second response time
- **🔍 Smart Query Validation**: Department mismatch detection
- **📊 Admin Panel**: Easy document upload and management
- **🎨 User-Friendly Interface**: Intuitive chat interface

## 🏗️ System Architecture

```
Multi-Department RAG System
├── Admin Panel (admin.py)
│   ├── Department-wise file upload
│   ├── Document processing & indexing
│   └── Index management
├── User Interface (app.py)
│   ├── Department selection
│   ├── Language selection
│   ├── Smart query processing
│   └── Department validation
├── Backend Services
│   ├── Department Manager
│   ├── Query Processor
│   ├── Document Service
│   └── Translation Service
└── Data Storage
    ├── FAISS Vector Indices
    ├── Department-specific uploads
    └── Processed documents
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "OPENAI_API_KEY=your_OPENAI_API_KEY_here" > .env
```

### 2. Test System

```bash
python test_system.py
```

### 3. Run Admin Panel

```bash
streamlit run admin.py
```

### 4. Run User Application

```bash
streamlit run app.py
```

## 📋 Detailed Usage Guide

### Admin Panel Usage

1. **Login**: Use credentials (admin/admin123)
2. **Select Department**: Choose from dropdown
3. **Upload Documents**: Upload PDF files for selected department
4. **Process & Index**: Click to create department-specific index
5. **Monitor Status**: Check index status for all departments

### User Interface Usage

1. **Select Department**: Choose your department from sidebar
2. **Select Language**: Pick your preferred response language
3. **Ask Questions**: Type questions related to selected department
4. **Get Responses**: Receive accurate, translated responses

### Smart Features

#### Department Validation
```python
# Example scenarios:
User selects: HR Department
User asks: "What is sales commission structure?"
Bot response: "🚨 Department Mismatch! You selected HR but asking about Sales. Please select Sales department or ask HR-related questions."
```

#### Multi-Language Support
```python
# Supported languages:
- English, Hindi, Tamil, Telugu, Bengali
- Malayalam, Kannada, Gujarati, Marathi
- Urdu, Odia, Assamese, Punjabi, Sindhi
- Nigerian languages: Yoruba, Igbo, Hausa
- Sinhala (Sri Lankan)
```

## 🔧 Configuration

### Department Keywords
```python
department_keywords = {
    'HR': ['policy', 'leave', 'employee', 'salary', 'benefits'],
    'Accounts': ['invoice', 'payment', 'budget', 'expense'],
    'Sales': ['sales', 'customer', 'lead', 'revenue'],
    # ... more departments
}
```

### System Settings
```python
class Config:
    DEPARTMENTS = ["HR", "Accounts", "Sales", "Marketing", "IT", "Operations", "Customer Support"]
    CHUNK_SIZE = 1500
    CHUNK_OVERLAP = 300
    EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
    LLM_MODEL = "gemini-1.5-flash"
```

## 📁 File Structure

```
baaten/
├── app.py                 # Main user interface
├── admin.py              # Admin panel
├── department_manager.py # Department management
├── product_scraper.py    # Product search functionality
├── test_system.py        # System testing
├── requirements.txt      # Dependencies
├── .env                  # Environment variables
├── uploads/              # Department-wise uploads
│   ├── hr/
│   ├── accounts/
│   └── ...
├── faiss_index/          # Vector indices
│   ├── hr/
│   ├── accounts/
│   └── ...
└── README.md            # This file
```

## 🎯 Core Functionality

### 1. Document Processing Pipeline
```
PDF Upload → Text Extraction → Chunking → Embedding → FAISS Index → Storage
```

### 2. Query Processing Pipeline
```
User Query → Department Validation → Document Retrieval → BM25 Reranking → LLM Response → Translation → User
```

### 3. Department Validation Logic
```python
def validate_department_query(query, selected_department):
    # Check if query matches selected department keywords
    # If mismatch detected, suggest correct department
    # Allow generic queries to pass through
```

## 🔍 Example Interactions

### Successful Query
```
User: Selects HR Department
User: "What is the leave policy?"
Bot: "**HR Department Response:**
Based on the HR policy document, here are the leave policies:
1. Annual Leave: 21 days per year
2. Sick Leave: 12 days per year
3. Maternity Leave: 180 days
..."
```

### Department Mismatch
```
User: Selects HR Department  
User: "What are the sales targets?"
Bot: "🚨 **Department Mismatch Alert!**
You have selected HR department, but your question seems to be related to Sales department.
Please:
1. Select Sales department from the sidebar, OR
2. Ask a question related to HR department"
```

## 🛠️ Troubleshooting

### Common Issues

1. **No Department Index Found**
   - Solution: Upload documents via admin panel and process them

2. **Translation Errors**
   - Solution: Check internet connection for Google Translate API

3. **Slow Response Times**
   - Solution: Reduce chunk size or optimize embedding model

4. **Department Validation Too Strict**
   - Solution: Adjust keyword lists in QueryProcessor class

## 🚀 Performance Optimization

### Response Time Optimization
- **Embedding Caching**: Models cached using `@st.cache_resource`
- **BM25 Reranking**: Fast document reranking for better relevance
- **Chunk Size Tuning**: Optimized for balance between context and speed
- **CPU Optimization**: Configured for CPU-only inference

### Memory Management
- **Lazy Loading**: Indices loaded only when needed
- **Resource Cleanup**: Proper cleanup of large objects
- **Batch Processing**: Efficient document processing

## 🔐 Security Features

- **Admin Authentication**: Login required for admin panel
- **Input Validation**: Query sanitization and validation
- **Safe File Handling**: Secure file upload and processing
- **Environment Variables**: Sensitive data in .env files

## 📈 Scalability

### Adding New Departments
1. Add department name to `Config.DEPARTMENTS`
2. Add keywords to `department_keywords`
3. Upload documents via admin panel
4. System automatically handles new department

### Adding New Languages
1. Add language to `Config.LANGUAGE_OPTIONS`
2. System automatically supports via Google Translate

## 🎉 Success Metrics

- ⚡ **Response Time**: < 10 seconds
- 🎯 **Accuracy**: Department-specific responses
- 🌐 **Language Support**: 18+ languages
- 🏢 **Department Coverage**: 7 departments
- 📊 **User Experience**: Intuitive interface

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📞 Support

For issues or questions:
1. Check troubleshooting section
2. Run `python test_system.py`
3. Contact system administrator

---

**Made with  for AIPL Group**

*Empowering every department with intelligent, multilingual AI assistance*

to run the terminal:conda activate C:\Users\anshu\Desktop\Ajit_group\ajit