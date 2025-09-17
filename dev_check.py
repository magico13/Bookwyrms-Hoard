#!/usr/bin/env python3
"""
Development script for type checking and testing.
"""

import subprocess
import sys
from pathlib import Path


def run_mypy() -> bool:
    """Run mypy type checking."""
    print("🔍 Running mypy type checking...")
    result = subprocess.run([
        sys.executable, "-m", "mypy", 
        "bookwyrms/", "main.py"
    ], cwd=Path(__file__).parent)
    
    if result.returncode == 0:
        print("✅ Type checking passed!")
        return True
    else:
        print("❌ Type checking failed!")
        return False


def run_test() -> bool:
    """Run a basic functionality test."""
    print("🧪 Running basic functionality test...")
    result = subprocess.run([
        sys.executable, "test_lookup.py"
    ], cwd=Path(__file__).parent)
    
    if result.returncode == 0:
        print("✅ Basic test passed!")
        return True
    else:
        print("❌ Basic test failed!")
        return False


def main() -> None:
    """Run all development checks."""
    print("🚀 Running development checks for Bookwyrms Hoard\n")
    
    checks_passed = 0
    total_checks = 2
    
    if run_mypy():
        checks_passed += 1
    
    print()
    
    if run_test():
        checks_passed += 1
    
    print(f"\n📊 Results: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("🎉 All checks passed! Ready for development.")
        sys.exit(0)
    else:
        print("⚠️  Some checks failed. Please fix issues before continuing.")
        sys.exit(1)


if __name__ == "__main__":
    main()