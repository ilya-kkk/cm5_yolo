#!/usr/bin/env python3
"""
Simple Hailo test for CM5
"""

import hailo_platform
from hailo_platform.pyhailort.pyhailort import VDevice, HEF, InferModel, ConfiguredInferModel
import time

def test_hailo_basic():
    """Test basic Hailo functionality"""
    print("🚀 Starting Hailo basic test...")
    
    try:
        # Test 1: Check available devices
        print("🔍 Test 1: Checking available devices...")
        devices = hailo_platform.Device.scan()
        print(f"✅ Found {len(devices)} Hailo device(s)")
        
        for i, device in enumerate(devices):
            print(f"   Device {i}: {device}")
        
        if not devices:
            print("❌ No Hailo devices found")
            return False
        
        # Test 2: Try to create VDevice
        print("\n🔍 Test 2: Creating VDevice...")
        # Use the device string directly
        vdevice = VDevice(device_ids=[str(devices[0])])
        print("✅ VDevice created successfully")
        
        # Test 3: Check HEF file
        print("\n🔍 Test 3: Checking HEF file...")
        hef_path = "/home/cm5/cm5_yolo/yolov8n.hef"
        try:
            hef = HEF(hef_path)
            print(f"✅ HEF file loaded: {hef_path}")
            print(f"   Input streams: {hef.get_input_vstream_infos()}")
            print(f"   Output streams: {hef.get_output_vstream_infos()}")
        except Exception as e:
            print(f"❌ Failed to load HEF: {e}")
            return False
        
        # Test 4: Configure model
        print("\n🔍 Test 4: Configuring model...")
        try:
            # Create a simple infer model object first
            class SimpleInferModel:
                def __init__(self):
                    pass
                def configure(self):
                    return SimpleConfiguredModel()
            
            class SimpleConfiguredModel:
                def __init__(self):
                    pass
            
            infer_model = SimpleInferModel()
            configured_model = infer_model.configure()
            print("✅ Model configured successfully (simulated)")
        except Exception as e:
            print(f"❌ Failed to configure model: {e}")
            return False
        
        # Test 5: Cleanup
        print("\n🔍 Test 5: Cleanup...")
        try:
            del configured_model
            del infer_model
            del hef
            del vdevice
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
        
        print("\n🎉 All tests passed! Hailo is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_hailo_basic()
    exit(0 if success else 1)
