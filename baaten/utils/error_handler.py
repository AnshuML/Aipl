"""
Centralized error handling and logging utilities
"""
import logging
import functools
import streamlit as st
from typing import Any, Callable, Optional, Union
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error"""
    def __init__(self, message: str, error_code: str = "GENERAL_ERROR"):
        self.message = message
        self.error_code = error_code
        self.timestamp = datetime.now()
        super().__init__(self.message)


class ValidationError(AppError):
    """Validation-related errors"""
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class ProcessingError(AppError):
    """Document processing errors"""
    def __init__(self, message: str):
        super().__init__(message, "PROCESSING_ERROR")


class AuthenticationError(AppError):
    """Authentication-related errors"""
    def __init__(self, message: str):
        super().__init__(message, "AUTH_ERROR")


def handle_errors(error_message: str = "An error occurred", 
                 show_details: bool = False):
    """Decorator for handling errors in functions"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except AppError as e:
                logger.error(f"Application error in {func.__name__}: {e.message}")
                if show_details:
                    st.error(f"❌ {e.message}")
                else:
                    st.error(f"❌ {error_message}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                if show_details:
                    st.error(f"❌ Unexpected error: {str(e)}")
                else:
                    st.error(f"❌ {error_message}")
                return None
        return wrapper
    return decorator


def safe_execute(func: Callable, *args, default_return=None, **kwargs) -> Any:
    """Safely execute a function with error handling"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {str(e)}")
        return default_return


class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_file_upload(file, max_size_mb: int = 10, allowed_types: list = None) -> bool:
        """Validate uploaded file"""
        if allowed_types is None:
            allowed_types = ['pdf']
        
        if not file:
            raise ValidationError("No file provided")
        
        # Check file size
        if hasattr(file, 'size') and file.size > max_size_mb * 1024 * 1024:
            raise ValidationError(f"File size exceeds {max_size_mb}MB limit")
        
        # Check file type
        file_extension = file.name.split('.')[-1].lower() if '.' in file.name else ''
        if file_extension not in allowed_types:
            raise ValidationError(f"File type '{file_extension}' not allowed. Allowed types: {allowed_types}")
        
        return True
    
    @staticmethod
    def validate_department(department: str, valid_departments: list) -> bool:
        """Validate department selection"""
        if not department:
            raise ValidationError("Department not specified")
        
        if department not in valid_departments:
            raise ValidationError(f"Invalid department: {department}")
        
        return True
    
    @staticmethod
    def validate_query(query: str, min_length: int = 3, max_length: int = 1000) -> bool:
        """Validate user query"""
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")
        
        query = query.strip()
        if len(query) < min_length:
            raise ValidationError(f"Query too short. Minimum {min_length} characters required")
        
        if len(query) > max_length:
            raise ValidationError(f"Query too long. Maximum {max_length} characters allowed")
        
        return True


class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    @staticmethod
    def time_function(func: Callable) -> Callable:
        """Decorator to time function execution"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"{func.__name__} executed in {execution_time:.2f} seconds")
                return result
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.error(f"{func.__name__} failed after {execution_time:.2f} seconds: {str(e)}")
                raise
        return wrapper
    
    @staticmethod
    def log_memory_usage(func: Callable) -> Callable:
        """Decorator to log memory usage (requires psutil)"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                import psutil
                process = psutil.Process()
                memory_before = process.memory_info().rss / 1024 / 1024  # MB
                
                result = func(*args, **kwargs)
                
                memory_after = process.memory_info().rss / 1024 / 1024  # MB
                memory_diff = memory_after - memory_before
                
                logger.info(f"{func.__name__} memory usage: {memory_diff:.2f}MB")
                return result
            except ImportError:
                # psutil not available, just execute function
                return func(*args, **kwargs)
        return wrapper


def create_error_boundary(component_name: str):
    """Create an error boundary for Streamlit components"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {component_name}: {str(e)}")
                st.error(f"❌ Error in {component_name}. Please try again or contact support.")
                
                # Show error details in expander for debugging
                with st.expander("Error Details (for debugging)"):
                    st.code(str(e))
                
                return None
        return wrapper
    return decorator