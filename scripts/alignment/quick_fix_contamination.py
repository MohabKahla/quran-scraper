#!/usr/bin/env python3
"""
Quick fix for contamination only - no alignment
This is much faster and doesn't require API
"""

import subprocess
import sys

print("=" * 80)
print("QUICK CONTAMINATION FIX")
print("=" * 80)
print("\nThis will only fix Arabic contamination (no API needed)")
print("Running auto_fix_all_issues.py with --no-alignment...\n")

try:
    result = subprocess.run([
        'python3',
        'auto_fix_all_issues.py',
        '--no-alignment'
    ])
    sys.exit(result.returncode)
except KeyboardInterrupt:
    print("\n\nInterrupted by user")
    sys.exit(1)
