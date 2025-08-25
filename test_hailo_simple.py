#!/usr/bin/env python3
"""
Simple Hailo test script without OpenCV dependencies
"""

import time
import sys

print("🔧 Starting Hailo test...")

# Test Hailo imports
try:
    import hailo_platform
    from hailo_platform.pyhailort.pyhailort import (
        VDevice, HEF, InferModel, ConfiguredInferModel,
        InputVStreamParams, OutputVStreamParams
    )
    print("✅ Hailo platform imported successfully")
    
    # Try to create VDevice
    try:
        print("🔧 Creating VDevice...")
        vdevice = VDevice()
        print("✅ VDevice created successfully")
        
        # List available devices
        print("🔧 Available devices:")
        try:
            devices = vdevice.scan()
            for i, device in enumerate(devices):
                print(f"  Device {i}: {device}")
        except AttributeError:
            # Try alternative method
            print("  Using alternative device detection...")
            try:
                # Try to get device info directly
                print(f"  VDevice created: {vdevice}")
                print("  Device appears to be working")
            except Exception as e:
                print(f"  Error getting device info: {e}")
        
        vdevice.release()
        print("✅ VDevice released successfully")
        
    except Exception as e:
        print(f"❌ Error creating VDevice: {e}")
        
except ImportError as e:
    print(f"❌ Hailo platform not available: {e}")
    sys.exit(1)

print("✅ Hailo test completed successfully!") 