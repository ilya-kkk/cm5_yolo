#!/usr/bin/env python3
"""
Test script for OpenCV
"""

import sys
import os

print("Python version:", sys.version)
print("Python path:", sys.path)
print("Current working directory:", os.getcwd())

try:
    import cv2
    print("✅ OpenCV imported successfully")
    print("OpenCV version:", cv2.__version__)
except ImportError as e:
    print(f"❌ Failed to import OpenCV: {e}")

try:
    import numpy as np
    print("✅ NumPy imported successfully")
    print("NumPy version:", np.__version__)
except ImportError as e:
    print(f"❌ Failed to import NumPy: {e}")

print("Test completed") 