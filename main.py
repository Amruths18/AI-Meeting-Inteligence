"""
Wrapper script - Run this from D:\2 to start Meeting Analyzer
This script automatically navigates to meeting_analyzer and runs the app
"""

import subprocess
import sys
from pathlib import Path

# Get the meeting_analyzer/main.py path
app_main = Path(__file__).parent / "meeting_analyzer" / "main.py"

if not app_main.exists():
    print(f"Error: {app_main} not found!")
    sys.exit(1)

# Run the actual main.py
subprocess.run([sys.executable, str(app_main)], check=False)
