#!/usr/bin/env python3
"""
Simple Hailo test script
"""

import sys
import os

# Add Hailo packages to path
sys.path.insert(0, '/usr/lib/python3/dist-packages')
sys.path.insert(0, '/usr/local/lib/python3/dist-packages')

print("=== Hailo Simple Test ===")
print("Python version:", sys.version)
print("Python executable:", sys.executable)
print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

# Try to import OpenCV
try:
    import cv2
    print("✅ OpenCV imported successfully")
    print("OpenCV version:", cv2.__version__)
except ImportError as e:
    print(f"❌ Failed to import OpenCV: {e}")

# Try to import Hailo
try:
    import hailo_platform
    print("✅ Hailo platform imported successfully")
    print("Hailo platform path:", hailo_platform.__file__)
    
    # Try to import specific Hailo classes
    try:
        from hailo_platform.pyhailort.pyhailort import VDevice, HEF
        print("✅ VDevice and HEF imported successfully")
        
        # Try to scan for devices
        try:
            devices = VDevice.scan()
            print(f"✅ Found {len(devices)} Hailo devices")
            for i, device in enumerate(devices):
                print(f"  Device {i}: {device}")
        except Exception as e:
            print(f"⚠️ Failed to scan devices: {e}")
            
    except ImportError as e:
        print(f"⚠️ Failed to import VDevice/HEF: {e}")
        
except ImportError as e:
    print(f"❌ Failed to import Hailo platform: {e}")
    print("Available paths:", sys.path)

print("=== Test completed ===") 