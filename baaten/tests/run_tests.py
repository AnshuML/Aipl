"""
Test runner for AIPL Chatbot
Runs all tests and generates reports
"""
import unittest
import sys
import os
import time
from io import StringIO
import json

# Add the parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResult:
    """Custom test result class to capture detailed results"""
    
    def __init__(self):
        self.tests_run = 0
        self.failures = []
        self.errors = []
        self.skipped = []
        self.success_count = 0
        self.start_time = None
        self.end_time = None
    
    def start_test_run(self):
        """Called when test run starts"""
        self.start_time = time.time()
    
    def stop_test_run(self):
        """Called when test run stops"""
        self.end_time = time.time()
    
    def add_success(self, test):
        """Add successful test"""
        self.success_count += 1
    
    def add_failure(self, test, err):
        """Add failed test"""
        self.failures.append((test, err))
    
    def add_error(self, test, err):
        """Add test with error"""
        self.errors.append((test, err))
    
    def add_skip(self, test, reason):
        """Add skipped test"""
        self.skipped.append((test, reason))
    
    @property
    def total_time(self):
        """Get total execution time"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    @property
    def success_rate(self):
        """Get success rate percentage"""
        if self.tests_run == 0:
            return 0
        return (self.success_count / self.tests_run) * 100


def run_test_suite(test_module_name, verbose=True):
    """Run a specific test suite"""
    print(f"\n{'='*60}")
    print(f"Running {test_module_name}")
    print(f"{'='*60}")
    
    try:
        # Import the test module
        test_module = __import__(test_module_name)
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_module)
        
        # Run tests
        if verbose:
            runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        else:
            runner = unittest.TextTestRunner(verbosity=1, stream=StringIO())
        
        result = runner.run(suite)
        
        # Print summary
        print(f"\n{test_module_name} Results:")
        print(f"  Tests run: {result.testsRun}")
        print(f"  Failures: {len(result.failures)}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Skipped: {len(result.skipped)}")
        print(f"  Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%" if result.testsRun > 0 else "N/A")
        
        return result
        
    except ImportError as e:
        print(f"Failed to import {test_module_name}: {e}")
        return None
    except Exception as e:
        print(f"Error running {test_module_name}: {e}")
        return None


def run_all_tests(verbose=True, include_performance=False):
    """Run all test suites"""
    print("AIPL Chatbot - Test Suite Runner")
    print("="*60)
    
    # Define test modules
    test_modules = [
        'test_config',
        'test_user_logger',
        'test_department_manager',
        'test_query_services',
        'test_translation_service',
        'test_security',
        'test_integration',
    ]
    
    # Add performance tests if requested
    if include_performance:
        test_modules.append('test_performance')
    
    # Track overall results
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    start_time = time.time()
    
    results = {}
    
    # Run each test module
    for module_name in test_modules:
        result = run_test_suite(module_name, verbose)
        
        if result:
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            total_skipped += len(result.skipped)
            
            results[module_name] = {
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'skipped': len(result.skipped),
                'success_rate': ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
            }
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Print overall summary
    print(f"\n{'='*60}")
    print("OVERALL TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total tests run: {total_tests}")
    print(f"Total failures: {total_failures}")
    print(f"Total errors: {total_errors}")
    print(f"Total skipped: {total_skipped}")
    print(f"Success rate: {((total_tests - total_failures - total_errors) / total_tests * 100):.1f}%" if total_tests > 0 else "N/A")
    print(f"Total time: {total_time:.2f} seconds")
    
    # Print detailed breakdown
    print(f"\nDETAILED BREAKDOWN:")
    print(f"{'Module':<25} {'Tests':<8} {'Pass':<8} {'Fail':<8} {'Error':<8} {'Skip':<8} {'Rate':<8}")
    print("-" * 80)
    
    for module_name, result in results.items():
        passed = result['tests_run'] - result['failures'] - result['errors']
        print(f"{module_name:<25} {result['tests_run']:<8} {passed:<8} {result['failures']:<8} {result['errors']:<8} {result['skipped']:<8} {result['success_rate']:.1f}%")
    
    # Generate JSON report
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_tests': total_tests,
        'total_failures': total_failures,
        'total_errors': total_errors,
        'total_skipped': total_skipped,
        'success_rate': ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0,
        'total_time': total_time,
        'modules': results
    }
    
    # Save report
    with open('test_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nTest report saved to: test_report.json")
    
    # Return overall success status
    return total_failures == 0 and total_errors == 0


def production_readiness_check():
    """Check if the system is ready for production"""
    print(f"\n{'='*60}")
    print("PRODUCTION READINESS CHECK")
    print(f"{'='*60}")
    
    checks = []
    
    # Run critical tests
    critical_modules = ['test_config', 'test_security', 'test_integration']
    
    for module_name in critical_modules:
        print(f"\nChecking {module_name}...")
        result = run_test_suite(module_name, verbose=False)
        
        if result:
            success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
            
            checks.append({
                'module': module_name,
                'success_rate': success_rate,
                'passed': success_rate >= 95,  # Require 95% success rate
                'failures': len(result.failures),
                'errors': len(result.errors)
            })
    
    # Evaluate readiness
    print(f"\nPRODUCTION READINESS RESULTS:")
    print("-" * 40)
    
    overall_ready = True
    
    for check in checks:
        status = "✅ PASS" if check['passed'] else "❌ FAIL"
        print(f"{check['module']:<25} {status} ({check['success_rate']:.1f}%)")
        
        if not check['passed']:
            overall_ready = False
            print(f"  Issues: {check['failures']} failures, {check['errors']} errors")
    
    print(f"\n{'='*40}")
    if overall_ready:
        print("🎉 SYSTEM IS PRODUCTION READY!")
        print("All critical tests passed with required success rates.")
    else:
        print("⚠️  SYSTEM NOT READY FOR PRODUCTION")
        print("Please fix the issues identified above before deploying.")
    print(f"{'='*40}")
    
    return overall_ready


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AIPL Chatbot Test Runner')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Run tests in verbose mode')
    parser.add_argument('--performance', '-p', action='store_true',
                       help='Include performance tests (slower)')
    parser.add_argument('--production-check', '-pc', action='store_true',
                       help='Run production readiness check')
    parser.add_argument('--module', '-m', type=str,
                       help='Run specific test module')
    
    args = parser.parse_args()
    
    if args.module:
        # Run specific module
        result = run_test_suite(args.module, args.verbose)
        sys.exit(0 if result and len(result.failures) == 0 and len(result.errors) == 0 else 1)
    
    elif args.production_check:
        # Run production readiness check
        ready = production_readiness_check()
        sys.exit(0 if ready else 1)
    
    else:
        # Run all tests
        success = run_all_tests(args.verbose, args.performance)
        
        if args.performance:
            print(f"\n📊 Performance tests included.")
            print("To skip performance tests in future runs, omit the -p flag.")
        
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
