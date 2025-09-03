"""
Unit tests for UserLogger module
"""
import unittest
import os
import tempfile
import shutil
import json
import csv
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import the module to test
from utils.user_logger import UserLogger


class TestUserLogger(unittest.TestCase):
    """Test UserLogger class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.logger = UserLogger()
        self.logger.logs_dir = self.test_dir
        self.test_email = "test@aiplabro.com"
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_ensure_logs_directory(self):
        """Test logs directory creation"""
        new_dir = os.path.join(self.test_dir, "new_logs")
        logger = UserLogger()
        logger.logs_dir = new_dir
        logger.ensure_logs_directory()
        self.assertTrue(os.path.exists(new_dir))
    
    def test_log_user_login_success(self):
        """Test successful login logging"""
        self.logger.log_user_login(self.test_email, True, "192.168.1.1")
        
        # Check CSV file
        csv_file = os.path.join(self.test_dir, "logins.csv")
        self.assertTrue(os.path.exists(csv_file))
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            self.assertEqual(row['email'], self.test_email)
            self.assertEqual(row['success'], 'True')
            self.assertEqual(row['ip_address'], "192.168.1.1")
    
    def test_log_user_login_failure(self):
        """Test failed login logging"""
        self.logger.log_user_login(self.test_email, False)
        
        # Check JSON file
        json_file = os.path.join(self.test_dir, "logins.json")
        self.assertTrue(os.path.exists(json_file))
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['email'], self.test_email)
            self.assertEqual(data[0]['success'], False)
    
    def test_log_user_question(self):
        """Test question logging"""
        question = "What is the leave policy?"
        department = "HR"
        language = "English"
        
        self.logger.log_user_question(self.test_email, question, department, language)
        
        # Check CSV file
        csv_file = os.path.join(self.test_dir, "questions.csv")
        self.assertTrue(os.path.exists(csv_file))
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            self.assertEqual(row['email'], self.test_email)
            self.assertEqual(row['question'], question)
            self.assertEqual(row['department'], department)
            self.assertEqual(row['language'], language)
    
    def test_log_bot_response_success(self):
        """Test successful bot response logging"""
        question = "What is the leave policy?"
        response = "Leave policy details..."
        response_time = 2.5
        
        self.logger.log_bot_response(
            self.test_email, question, response, True, response_time
        )
        
        # Check CSV file
        csv_file = os.path.join(self.test_dir, "responses.csv")
        self.assertTrue(os.path.exists(csv_file))
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            self.assertEqual(row['email'], self.test_email)
            self.assertEqual(row['success'], 'True')
            self.assertEqual(float(row['response_time_seconds']), response_time)
    
    def test_log_bot_response_failure(self):
        """Test failed bot response logging"""
        question = "What is the leave policy?"
        response = "Error occurred"
        response_time = 1.0
        
        self.logger.log_bot_response(
            self.test_email, question, response, False, response_time
        )
        
        # Check JSON file
        json_file = os.path.join(self.test_dir, "responses.json")
        self.assertTrue(os.path.exists(json_file))
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['email'], self.test_email)
            self.assertEqual(data[0]['success'], False)
    
    def test_log_user_logout(self):
        """Test user logout logging"""
        self.logger.log_user_logout(self.test_email)
        
        # Check CSV file
        csv_file = os.path.join(self.test_dir, "logouts.csv")
        self.assertTrue(os.path.exists(csv_file))
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            self.assertEqual(row['email'], self.test_email)
            self.assertEqual(row['event_type'], "LOGOUT")
    
    def test_log_error(self):
        """Test error logging"""
        error_type = "API Error"
        error_message = "Connection timeout"
        
        self.logger.log_error(self.test_email, error_type, error_message)
        
        # Check CSV file
        csv_file = os.path.join(self.test_dir, "errors.csv")
        self.assertTrue(os.path.exists(csv_file))
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            self.assertEqual(row['email'], self.test_email)
            self.assertEqual(row['error_type'], error_type)
            self.assertEqual(row['error_message'], error_message)
    
    def test_save_to_csv_new_file(self):
        """Test saving to new CSV file"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'TEST',
            'email': self.test_email
        }
        
        self.logger.save_to_csv('test.csv', data)
        
        csv_file = os.path.join(self.test_dir, 'test.csv')
        self.assertTrue(os.path.exists(csv_file))
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            self.assertEqual(row['email'], self.test_email)
    
    def test_save_to_csv_existing_file(self):
        """Test appending to existing CSV file"""
        data1 = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'TEST1',
            'email': 'user1@test.com'
        }
        data2 = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'TEST2',
            'email': 'user2@test.com'
        }
        
        self.logger.save_to_csv('test.csv', data1)
        self.logger.save_to_csv('test.csv', data2)
        
        csv_file = os.path.join(self.test_dir, 'test.csv')
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['email'], 'user1@test.com')
            self.assertEqual(rows[1]['email'], 'user2@test.com')
    
    def test_save_to_json_new_file(self):
        """Test saving to new JSON file"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'TEST',
            'email': self.test_email
        }
        
        self.logger.save_to_json('test.json', data)
        
        json_file = os.path.join(self.test_dir, 'test.json')
        self.assertTrue(os.path.exists(json_file))
        
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            self.assertEqual(len(json_data), 1)
            self.assertEqual(json_data[0]['email'], self.test_email)
    
    def test_save_to_json_existing_file(self):
        """Test appending to existing JSON file"""
        data1 = {'email': 'user1@test.com', 'event': 'TEST1'}
        data2 = {'email': 'user2@test.com', 'event': 'TEST2'}
        
        self.logger.save_to_json('test.json', data1)
        self.logger.save_to_json('test.json', data2)
        
        json_file = os.path.join(self.test_dir, 'test.json')
        
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            self.assertEqual(len(json_data), 2)
            self.assertEqual(json_data[0]['email'], 'user1@test.com')
            self.assertEqual(json_data[1]['email'], 'user2@test.com')
    
    def test_get_user_stats(self):
        """Test user statistics calculation"""
        # Create test data
        self.logger.log_user_login(self.test_email, True)
        self.logger.log_user_login(self.test_email, True)
        self.logger.log_user_question(self.test_email, "Question 1", "HR", "English")
        self.logger.log_user_question(self.test_email, "Question 2", "Accounts", "Hindi")
        self.logger.log_bot_response(self.test_email, "Q1", "R1", True, 1.5)
        self.logger.log_bot_response(self.test_email, "Q2", "R2", False, 2.0)
        
        stats = self.logger.get_user_stats(self.test_email)
        
        self.assertEqual(stats['total_logins'], 2)
        self.assertEqual(stats['total_questions'], 2)
        self.assertEqual(stats['total_responses'], 2)
        self.assertEqual(stats['successful_responses'], 1)
        self.assertIn('HR', stats['departments_used'])
        self.assertIn('Accounts', stats['departments_used'])
        self.assertIn('English', stats['languages_used'])
        self.assertIn('Hindi', stats['languages_used'])
    
    def test_get_daily_report(self):
        """Test daily report generation"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Create test data for today
        self.logger.log_user_login(self.test_email, True)
        self.logger.log_user_login("user2@test.com", True)
        self.logger.log_user_question(self.test_email, "Question 1", "HR", "English")
        
        report = self.logger.get_daily_report(today)
        
        self.assertEqual(report['date'], today)
        self.assertEqual(report['total_logins'], 2)
        self.assertEqual(report['total_questions'], 1)
        self.assertEqual(len(report['unique_users']), 2)
        self.assertIn(self.test_email, report['unique_users'])
        self.assertIn("user2@test.com", report['unique_users'])
    
    def test_empty_stats(self):
        """Test statistics with no data"""
        stats = self.logger.get_user_stats("nonexistent@test.com")
        
        self.assertEqual(stats['total_logins'], 0)
        self.assertEqual(stats['total_questions'], 0)
        self.assertEqual(stats['total_responses'], 0)
        self.assertEqual(stats['successful_responses'], 0)
        self.assertEqual(len(stats['departments_used']), 0)
        self.assertEqual(len(stats['languages_used']), 0)


class TestUserLoggerIntegration(unittest.TestCase):
    """Integration tests for UserLogger"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.logger = UserLogger()
        self.logger.logs_dir = self.test_dir
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_complete_user_session(self):
        """Test a complete user session logging"""
        email = "integration@test.com"
        
        # Login
        self.logger.log_user_login(email, True, "192.168.1.1")
        
        # Ask questions
        self.logger.log_user_question(email, "What is leave policy?", "HR", "English")
        self.logger.log_bot_response(email, "What is leave policy?", "Leave policy is...", True, 1.2)
        
        self.logger.log_user_question(email, "How to claim expenses?", "Accounts", "English")
        self.logger.log_bot_response(email, "How to claim expenses?", "Expense process...", True, 0.8)
        
        # Logout
        self.logger.log_user_logout(email)
        
        # Verify all files exist
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "logins.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "questions.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "responses.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "logouts.csv")))
        
        # Check user stats
        stats = self.logger.get_user_stats(email)
        self.assertEqual(stats['total_logins'], 1)
        self.assertEqual(stats['total_questions'], 2)
        self.assertEqual(stats['total_responses'], 2)
        self.assertEqual(stats['successful_responses'], 2)


if __name__ == '__main__':
    unittest.main()
