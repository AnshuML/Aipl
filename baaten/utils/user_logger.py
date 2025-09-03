"""
User Activity Logger for AIPL Chatbot
Captures all user interactions, logins, questions, and responses
"""
import json
import os
import csv
from datetime import datetime
import logging
from typing import Dict, Any, Optional

class UserLogger:
    """Comprehensive user activity logger"""
    
    def __init__(self):
        self.logs_dir = "user_logs"
        self.ensure_logs_directory()
        self.setup_logging()
    
    def ensure_logs_directory(self):
        """Create logs directory if it doesn't exist"""
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = os.path.join(self.logs_dir, "user_activity.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def log_user_login(self, email: str, success: bool, user_name: str = "", ip_address: str = "unknown"):
        """Log user login attempt"""
        login_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "LOGIN",
            "email": email,
            "user_name": user_name,
            "success": success,
            "ip_address": ip_address
        }
        
        # Log to file
        if user_name:
            self.logger.info(f"LOGIN - Name: {user_name}, Email: {email}, Success: {success}, IP: {ip_address}")
        else:
            self.logger.info(f"LOGIN - Email: {email}, Success: {success}, IP: {ip_address}")
        
        # Save to CSV
        self.save_to_csv("logins.csv", login_data)
        
        # Save to JSON
        self.save_to_json("logins.json", login_data)
    
    def log_user_question(self, email: str, question: str, department: str, language: str):
        """Log user question"""
        question_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "QUESTION",
            "email": email,
            "question": question,
            "department": department,
            "language": language
        }
        
        # Log to file
        self.logger.info(f"QUESTION - Email: {email}, Department: {department}, Language: {language}, Question: {question[:100]}...")
        
        # Save to CSV
        self.save_to_csv("questions.csv", question_data)
        
        # Save to JSON
        self.save_to_json("questions.json", question_data)
    
    def log_bot_response(self, email: str, question: str, response: str, success: bool, response_time: float):
        """Log bot response"""
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "RESPONSE",
            "email": email,
            "question": question[:200],  # Truncate for storage
            "response": response[:500],  # Truncate for storage
            "success": success,
            "response_time_seconds": response_time
        }
        
        # Log to file
        self.logger.info(f"RESPONSE - Email: {email}, Success: {success}, Time: {response_time:.2f}s")
        
        # Save to CSV
        self.save_to_csv("responses.csv", response_data)
        
        # Save to JSON
        self.save_to_json("responses.json", response_data)
    
    def log_user_logout(self, email: str):
        """Log user logout"""
        logout_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "LOGOUT",
            "email": email
        }
        
        # Log to file
        self.logger.info(f"LOGOUT - Email: {email}")
        
        # Save to CSV
        self.save_to_csv("logouts.csv", logout_data)
        
        # Save to JSON
        self.save_to_json("logouts.json", logout_data)
    
    def log_error(self, email: str, error_type: str, error_message: str):
        """Log errors"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "ERROR",
            "email": email,
            "error_type": error_type,
            "error_message": error_message
        }
        
        # Log to file
        self.logger.error(f"ERROR - Email: {email}, Type: {error_type}, Message: {error_message}")
        
        # Save to CSV
        self.save_to_csv("errors.csv", error_data)
        
        # Save to JSON
        self.save_to_json("errors.json", error_data)
    
    def save_to_csv(self, filename: str, data: Dict[str, Any]):
        """Save data to CSV file"""
        filepath = os.path.join(self.logs_dir, filename)
        file_exists = os.path.exists(filepath)
        
        with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=data.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)
    
    def save_to_json(self, filename: str, data: Dict[str, Any]):
        """Save data to JSON file"""
        filepath = os.path.join(self.logs_dir, filename)
        
        # Load existing data
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except:
                    existing_data = []
        else:
            existing_data = []
        
        # Append new data
        existing_data.append(data)
        
        # Save back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
    
    def get_user_stats(self, email: str) -> Dict[str, Any]:
        """Get statistics for a specific user"""
        stats = {
            "total_logins": 0,
            "total_questions": 0,
            "total_responses": 0,
            "successful_responses": 0,
            "average_response_time": 0,
            "departments_used": set(),
            "languages_used": set()
        }
        
        # Read from CSV files
        for filename in ["logins.csv", "questions.csv", "responses.csv"]:
            filepath = os.path.join(self.logs_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('email') == email:
                            if filename == "logins.csv":
                                stats["total_logins"] += 1
                            elif filename == "questions.csv":
                                stats["total_questions"] += 1
                                stats["departments_used"].add(row.get('department', ''))
                                stats["languages_used"].add(row.get('language', ''))
                            elif filename == "responses.csv":
                                stats["total_responses"] += 1
                                if row.get('success') == 'True':
                                    stats["successful_responses"] += 1
        
        # Convert sets to lists for JSON serialization
        stats["departments_used"] = list(stats["departments_used"])
        stats["languages_used"] = list(stats["languages_used"])
        
        return stats
    
    def get_daily_report(self, date: str = None) -> Dict[str, Any]:
        """Get daily activity report"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        report = {
            "date": date,
            "total_logins": 0,
            "total_questions": 0,
            "total_responses": 0,
            "unique_users": set(),
            "departments_used": set(),
            "languages_used": set()
        }
        
        # Read from CSV files
        for filename in ["logins.csv", "questions.csv", "responses.csv"]:
            filepath = os.path.join(self.logs_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if date in row.get('timestamp', ''):
                            if filename == "logins.csv":
                                report["total_logins"] += 1
                                report["unique_users"].add(row.get('email', ''))
                            elif filename == "questions.csv":
                                report["total_questions"] += 1
                                report["unique_users"].add(row.get('email', ''))
                                report["departments_used"].add(row.get('department', ''))
                                report["languages_used"].add(row.get('language', ''))
                            elif filename == "responses.csv":
                                report["total_responses"] += 1
                                report["unique_users"].add(row.get('email', ''))
        
        # Convert sets to lists
        report["unique_users"] = list(report["unique_users"])
        report["departments_used"] = list(report["departments_used"])
        report["languages_used"] = list(report["languages_used"])
        
        return report

# Global logger instance
user_logger = UserLogger()
