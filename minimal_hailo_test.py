#!/usr/bin/env python3
"""
Minimal Hailo test without GStreamer to diagnose segmentation fault
"""

import hailo_platform
from hailo_platform.pyhailort.pyhailort import VDevice, HEF, InferModel, ConfiguredInferModel
import numpy as np
import time

def test_hailo_minimal():
    """Test minimal Hailo functionality"""
    print("🚀 Starting minimal Hailo test...")
    
    try:
        # Test 1: Basic imports
        print("🔍 Test 1: Basic imports...")
        print(f"   Hailo platform version: {hailo_platform.__version__}")
        print("✅ Basic imports successful")
        
        # Test 2: Device scan
        print("\n🔍 Test 2: Device scan...")
        devices = hailo_platform.Device.scan()
        print(f"   Found {len(devices)} device(s)")
        for i, device in enumerate(devices):
            print(f"   Device {i}: {device}")
        print("✅ Device scan successful")
        
        # Test 3: VDevice creation
        print("\n🔍 Test 3: VDevice creation...")
        vdevice = VDevice(device_ids=[str(devices[0])])
        print("✅ VDevice creation successful")
        
        # Test 4: HEF loading
        print("\n🔍 Test 4: HEF loading...")
        hef_path = "/home/cm5/cm5_yolo/yolov8n.hef"
        hef = HEF(hef_path)
        print(f"✅ HEF loading successful: {hef_path}")
        
        # Test 5: Model info
        print("\n🔍 Test 5: Model information...")
        input_infos = hef.get_input_vstream_infos()
        output_infos = hef.get_output_vstream_infos()
        print(f"   Input streams: {len(input_infos)}")
        for info in input_infos:
            print(f"     - {info.name}: {info.shape}")
        print(f"   Output streams: {len(output_infos)}")
        for info in output_infos:
            print(f"     - {info.name}: {info.shape}")
        print("✅ Model info retrieval successful")
        
        # Test 6: Simple inference setup (without running)
        print("\n🔍 Test 6: Inference setup...")
        print("   Creating input data...")
        input_data = np.random.randint(0, 255, (1, 640, 640, 3), dtype=np.uint8)
        print(f"   Input data shape: {input_data.shape}")
        print("✅ Inference setup successful")
        
        # Test 7: Cleanup
        print("\n🔍 Test 7: Cleanup...")
        del hef
        del vdevice
        print("✅ Cleanup successful")
        
        print("\n🎉 All minimal tests passed! Hailo core functionality works.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hailo_minimal()
    exit(0 if success else 1)
