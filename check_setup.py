#!/usr/bin/env python
"""Check if all dependencies are installed and working"""

import sys

print("="*60)
print("DASH Application - Dependency Check")
print("="*60)
print()

errors = []
warnings = []

# Check Python version
print(f"✓ Python version: {sys.version.split()[0]}")

# Check Flask
try:
    import flask
    print(f"✓ Flask: {flask.__version__}")
except ImportError:
    errors.append("Flask not installed. Run: pip install flask")
    print("✗ Flask: NOT INSTALLED")

# Check Google Generative AI
try:
    import google.generativeai as genai
    print(f"✓ Google Generative AI: Installed")
except ImportError as e:
    errors.append("google-generativeai not installed. Run: pip install google-generativeai")
    print(f"✗ Google Generative AI: NOT INSTALLED - {e}")

# Check PyPDF2
try:
    import PyPDF2
    print(f"✓ PyPDF2: {PyPDF2.__version__}")
except ImportError:
    errors.append("PyPDF2 not installed. Run: pip install PyPDF2")
    print("✗ PyPDF2: NOT INSTALLED")

# Check Pandas
try:
    import pandas as pd
    print(f"✓ Pandas: {pd.__version__}")
except ImportError:
    errors.append("Pandas not installed. Run: pip install pandas")
    print("✗ Pandas: NOT INSTALLED")

print()
print("="*60)

if errors:
    print("❌ ERRORS FOUND:")
    for i, error in enumerate(errors, 1):
        print(f"  {i}. {error}")
    print()
    print("Fix command:")
    print("  pip install flask google-generativeai PyPDF2 pandas")
    sys.exit(1)
else:
    print("✅ ALL DEPENDENCIES INSTALLED!")
    print()
    print("You can now run the application:")
    print("  python app.py")
    print()
    print("Or use the batch file:")
    print("  run_app.bat")
    sys.exit(0)
