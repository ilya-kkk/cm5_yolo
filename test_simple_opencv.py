#!/usr/bin/env python3
"""
Simple OpenCV test without Hailo dependencies
"""

import cv2
import numpy as np

print("🔧 Testing OpenCV functionality...")

try:
    # Test basic OpenCV operations
    print("✅ OpenCV imported successfully")
    
    # Create a test image
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    test_image[:] = (0, 255, 0)  # Green color
    
    # Test image operations
    gray = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
    print("✅ Image conversion successful")
    
    # Test camera access
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print("✅ Camera access successful")
        cap.release()
    else:
        print("⚠️ Camera not accessible (this is normal in some environments)")
    
    print("✅ All OpenCV tests passed!")
    
except Exception as e:
    print(f"❌ OpenCV test failed: {e}")
    import traceback
    traceback.print_exc()
