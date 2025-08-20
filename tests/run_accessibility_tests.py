#!/usr/bin/env python3
"""
Accessibility Test Runner for Voice Exam System
Run this script to perform comprehensive accessibility testing
"""

import os
import sys
import subprocess
import unittest
from tests.test_accessibility import AccessibilityTestCase


def setup_test_environment():
    """Ensure Django is properly configured for testing"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sneportal.settings')
    
    import django
    django.setup()


def run_accessibility_tests():
    """Run all accessibility tests and generate reports"""
    print("🚀 Starting Accessibility Test Suite for Voice Exam System")
    print("=" * 60)
    
    # Set up test environment
    setup_test_environment()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(AccessibilityTestCase)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("🎯 ACCESSIBILITY TEST SUMMARY")
    print("=" * 60)
    
    if result.wasSuccessful():
        print("✅ ALL ACCESSIBILITY TESTS PASSED!")
        print("Your application meets accessibility standards.")
    else:
        print("❌ SOME ACCESSIBILITY TESTS FAILED")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        
        if result.failures:
            print("\n🔍 FAILURES:")
            for test, failure in result.failures:
                print(f"  - {test}: {failure.split('AssertionError:')[-1].strip()}")
                
        if result.errors:
            print("\n⚠️ ERRORS:")
            for test, error in result.errors:
                print(f"  - {test}: {error.split('Exception:')[-1].strip()}")
    
    print("\n📋 NEXT STEPS:")
    print("1. Review accessibility_report.json for detailed findings")
    print("2. Fix any critical or serious violations")
    print("3. Re-run tests after making changes")
    print("4. Consider manual testing with screen readers")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_accessibility_tests()
    sys.exit(0 if success else 1)