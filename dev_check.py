#!/usr/bin/env python3
"""
Development script for type checking and testing.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Set


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
    
    # Run inline test instead of external script
    try:
        from bookwyrms.lookup import BookLookupService
        
        service = BookLookupService()
        test_isbn = "9780134685991"  # Effective Java
        
        book_info = service.get_book_info(test_isbn)
        
        if book_info and book_info.title and book_info.authors:
            print(f"✅ Found: '{book_info.title}' by {', '.join(book_info.authors)}")
            print("✅ Basic test passed!")
            return True
        else:
            print("❌ Test failed: No book info returned")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def get_installed_packages() -> Dict[str, str]:
    """Get currently installed package versions."""
    import pkg_resources
    
    # Get main packages from requirements.txt
    requirements_file = Path(__file__).parent / "requirements.txt"
    main_packages: Set[str] = set()
    
    if requirements_file.exists():
        with open(requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # Extract package name (before >=, ==, etc.)
                    pkg_name = line.split('>=')[0].split('==')[0].split('<')[0].strip()
                    if pkg_name:
                        main_packages.add(pkg_name)
    
    # Get installed versions
    installed: Dict[str, str] = {}
    for pkg in main_packages:
        try:
            version = pkg_resources.get_distribution(pkg).version
            installed[pkg] = version
        except pkg_resources.DistributionNotFound:
            pass  # Skip packages that aren't installed
    
    return installed


def check_package_updates() -> bool:
    """Check for available package updates."""
    print("📦 Checking for package updates...")
    
    try:
        import requests
    except ImportError:
        print("❌ requests not available for version checking")
        return False
    
    installed_packages = get_installed_packages()
    if not installed_packages:
        print("❌ No packages found to check")
        return False
    
    updates_available: List[Tuple[str, str, str]] = []
    
    for pkg, current_version in installed_packages.items():
        try:
            r = requests.get(f'https://pypi.org/pypi/{pkg}/json', timeout=5)
            r.raise_for_status()
            latest = r.json()['info']['version']
            
            # Simple version comparison (works for most cases)
            if latest != current_version:
                updates_available.append((pkg, current_version, latest))
                
        except Exception as e:
            print(f"⚠️  Error checking {pkg}: {e}")
    
    if updates_available:
        print("📋 Updates available:")
        for pkg, current, latest in updates_available:
            print(f"  • {pkg}: {current} → {latest}")
        print("💡 Run 'pip install --upgrade <package>' to update")
        return True
    else:
        print("✅ All packages are up to date!")
        return True


def main() -> None:
    """Run all development checks."""
    parser = argparse.ArgumentParser(description="Run development checks for Bookwyrm's Hoard")
    parser.add_argument("--check-updates", action="store_true", 
                       help="Also check for package updates")
    parser.add_argument("--updates-only", action="store_true",
                       help="Only check for package updates")
    
    args = parser.parse_args()
    
    if args.updates_only:
        print("📦 Checking package updates only\n")
        check_package_updates()
        return
    
    print("🚀 Running development checks for Bookwyrm's Hoard\n")
    
    checks_passed = 0
    total_checks = 2
    
    if run_mypy():
        checks_passed += 1
    
    print()
    
    if run_test():
        checks_passed += 1
    
    if args.check_updates:
        print()
        check_package_updates()
    
    print(f"\n📊 Results: {checks_passed}/{total_checks} core checks passed")
    
    if checks_passed == total_checks:
        print("🎉 All checks passed! Ready for development.")
        sys.exit(0)
    else:
        print("⚠️  Some checks failed. Please fix issues before continuing.")
        sys.exit(1)


if __name__ == "__main__":
    main()