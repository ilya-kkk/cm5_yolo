#!/usr/bin/env python3
"""
Simple test script for OpenCV
"""

import sys
import os

print("=== Simple OpenCV Test ===")
print("Python version:", sys.version)
print("Python executable:", sys.executable)
print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

# Try to import OpenCV
try:
    import cv2
    print("✅ OpenCV imported successfully")
    print("OpenCV version:", cv2.__version__)
    print("OpenCV path:", cv2.__file__)
except ImportError as e:
    print(f"❌ Failed to import OpenCV: {e}")
    print("Available paths:", sys.path)
    
    # Try to find cv2 module
    import importlib.util
    for path in sys.path:
        if os.path.exists(path):
            cv2_path = os.path.join(path, 'cv2')
            if os.path.exists(cv2_path):
                print(f"Found cv2 at: {cv2_path}")
                if os.path.isdir(cv2_path):
                    print(f"cv2 is a directory, contents: {os.listdir(cv2_path)}")
                else:
                    print(f"cv2 is a file, size: {os.path.getsize(cv2_path)}")

print("Test completed") 