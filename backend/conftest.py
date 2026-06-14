"""Root conftest for backend tests.

Ensures backend package is importable regardless of which test directory pytest runs in.
"""
import os
import sys

# Add project root to sys.path so `backend.*` imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
