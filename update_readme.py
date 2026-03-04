#!/usr/bin/env python3
"""Wrapper: run the generator from repo root with `python3 update_readme.py`."""
import os
import subprocess
import sys

repo_root = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(repo_root, "GitTrendHub", "update_readme.py")
if not os.path.isfile(script_path):
    print(f"Error: generator script not found: {script_path}")
    sys.exit(1)
result = subprocess.run([sys.executable, script_path], cwd=repo_root)
sys.exit(result.returncode)
