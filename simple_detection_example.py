#!/usr/bin/env python3
"""
Simple object detection example using Hailo API
"""

import hailo_platform
from hailo_platform.pyhailort.pyhailort import VDevice, HEF, InputVStreamParams, OutputVStreamParams
import numpy as np
import cv2
import time

def create_test_image(width=640, height=640):
    """Create a test image with some shapes"""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Draw some test shapes
    cv2.rectangle(img, (100, 100), (200, 200), (255, 0, 0), -1)  # Blue rectangle
    cv2.circle(img, (400, 300), 50, (0, 255, 0), -1)  # Green circle
    cv2.rectangle(img, (500, 400), (600, 500), (0, 0, 255), -1)  # Red rectangle
    
    return img

def simple_detection_demo():
    """Simple detection demo using Hailo"""
    print("🚀 Starting simple detection demo...")
    
    try:
        # Step 1: Initialize Hailo device
        print("🔧 Step 1: Initializing Hailo device...")
        devices = hailo_platform.Device.scan()
        if not devices:
            print("❌ No Hailo devices found")
            return False
        
        print(f"✅ Found Hailo device: {devices[0]}")
        vdevice = VDevice(device_ids=[str(devices[0])])
        print("✅ VDevice created successfully")
        
        # Step 2: Load HEF file
        print("\n🔧 Step 2: Loading HEF file...")
        hef_path = "/home/cm5/cm5_yolo/yolov8n.hef"
        hef = HEF(hef_path)
        print(f"✅ HEF loaded: {hef_path}")
        
        # Step 3: Get model info
        print("\n🔧 Step 3: Getting model information...")
        input_infos = hef.get_input_vstream_infos()
        output_infos = hef.get_output_vstream_infos()
        
        print(f"   Input streams: {len(input_infos)}")
        for info in input_infos:
            print(f"     - {info.name}: {info.shape} ({info.format})")
        
        print(f"   Output streams: {len(output_infos)}")
        for info in output_infos:
            print(f"     - {info.name}: {info.shape} ({info.format})")
        
        # Step 4: Create test image
        print("\n🔧 Step 4: Creating test image...")
        test_img = create_test_image(640, 640)
        print(f"✅ Test image created: {test_img.shape}")
        
        # Step 5: Simulate inference (since we can't run full inference without hailo-apps-infra)
        print("\n🔧 Step 5: Simulating inference...")
        print("   📊 Input image size: 640x640x3")
        print("   🎯 Model: YOLOv8n (nano)")
        print("   📈 Expected output: Detection results with bounding boxes")
        
        # Simulate processing time
        time.sleep(1)
        print("   ⏱️ Processing time: ~1ms (simulated)")
        
        # Step 6: Display results
        print("\n🔧 Step 6: Results...")
        print("   🎯 Detected objects (simulated):")
        print("     - Rectangle at (100, 100) - (200, 200)")
        print("     - Circle at center (400, 300)")
        print("     - Rectangle at (500, 400) - (600, 500)")
        
        # Step 7: Cleanup
        print("\n🔧 Step 7: Cleanup...")
        del hef
        del vdevice
        print("✅ Cleanup completed")
        
        print("\n🎉 Demo completed successfully!")
        print("💡 To run full inference, you need hailo-apps-infra package")
        print("🌐 Check: https://github.com/hailo-ai/hailo-apps-infra")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        return False

if __name__ == "__main__":
    success = simple_detection_demo()
    exit(0 if success else 1)
