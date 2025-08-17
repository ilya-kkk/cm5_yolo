#!/usr/bin/env python3
"""
Basic Hailo test script for CM5
Tests Hailo device detection and basic functionality
"""

import sys
import os
import time

# Add Hailo packages to path
sys.path.insert(0, '/usr/lib/python3/dist-packages')
sys.path.insert(0, '/usr/local/lib/python3/dist-packages')

print("=== Hailo Basic Test ===")
print("Python version:", sys.version)
print("Python executable:", sys.executable)
print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

# Test 1: Basic imports
print("\n🔍 Test 1: Basic imports")
try:
    import cv2
    print("✅ OpenCV imported successfully")
    print("OpenCV version:", cv2.__version__)
except ImportError as e:
    print(f"❌ Failed to import OpenCV: {e}")

# Test 2: Hailo platform import
print("\n🔍 Test 2: Hailo platform import")
try:
    import hailo_platform
    print("✅ Hailo platform imported successfully")
    print("Hailo platform path:", hailo_platform.__file__)
    print("Hailo platform version:", getattr(hailo_platform, '__version__', 'Unknown'))
except ImportError as e:
    print(f"❌ Failed to import Hailo platform: {e}")
    print("Available paths:", sys.path)

# Test 3: Hailo specific classes
print("\n🔍 Test 3: Hailo specific classes")
if 'hailo_platform' in sys.modules:
    try:
        from hailo_platform.pyhailort.pyhailort import VDevice, HEF
        print("✅ VDevice and HEF imported successfully")
        
        # Test 4: Device scanning
        print("\n🔍 Test 4: Device scanning")
        try:
            devices = VDevice.scan()
            print(f"✅ Found {len(devices)} Hailo devices")
            for i, device in enumerate(devices):
                print(f"  Device {i}: {device}")
                print(f"    Device ID: {getattr(device, 'device_id', 'Unknown')}")
                print(f"    Status: {getattr(device, 'status', 'Unknown')}")
        except Exception as e:
            print(f"⚠️ Failed to scan devices: {e}")
            
    except ImportError as e:
        print(f"⚠️ Failed to import VDevice/HEF: {e}")
        print("Available Hailo modules:", dir(hailo_platform))

# Test 5: HEF file detection
print("\n🔍 Test 5: HEF file detection")
hef_paths = [
    "/workspace/yolov8n.hef",
    "/home/cm5/yolo_models/yolov8n.hef",
    "/usr/local/share/yolo/yolov8n.hef",
    "/opt/yolo/yolov8n.hef",
    "yolov8n.hef"
]

found_hef = None
for path in hef_paths:
    if os.path.exists(path):
        found_hef = path
        print(f"✅ Found HEF file: {path}")
        print(f"   Size: {os.path.getsize(path) / (1024*1024):.1f} MB")
        break

if not found_hef:
    print("❌ No HEF file found in common locations")

# Test 6: Model loading (if HEF found and Hailo available)
print("\n🔍 Test 6: Model loading")
if found_hef and 'hailo_platform' in sys.modules:
    try:
        from hailo_platform.pyhailort.pyhailort import HEF
        
        hef = HEF(found_hef)
        print("✅ HEF loaded successfully")
        
        # Get model info
        network_groups = hef.get_network_group_names()
        print(f"📋 Network groups: {network_groups}")
        
        if network_groups:
            first_network = network_groups[0]
            print(f"🎯 First network: {first_network}")
            
            # Get input/output info
            input_infos = hef.get_input_vstream_infos(first_network)
            output_infos = hef.get_output_vstream_infos(first_network)
            
            print(f"📥 Input streams: {len(input_infos)}")
            for i, info in enumerate(input_infos):
                print(f"  Input {i}: shape={info.shape}, format={info.format}")
            
            print(f"📤 Output streams: {len(output_infos)}")
            for i, info in enumerate(output_infos):
                print(f"  Output {i}: shape={info.shape}, format={info.format}")
        
    except Exception as e:
        print(f"❌ Failed to load HEF: {e}")

# Test 7: System information
print("\n🔍 Test 7: System information")
try:
    import subprocess
    
    # Check PCI devices
    result = subprocess.run(['lspci'], capture_output=True, text=True)
    if result.returncode == 0:
        pci_output = result.stdout
        if 'Hailo' in pci_output or 'hailo' in pci_output.lower():
            print("✅ Hailo device found in PCI")
        else:
            print("⚠️ No Hailo device found in PCI devices")
            print("PCI devices:")
            for line in pci_output.split('\n')[:10]:  # Show first 10
                if line.strip():
                    print(f"  {line}")
    else:
        print("⚠️ Could not check PCI devices")
        
    # Check loaded modules
    result = subprocess.run(['lsmod'], capture_output=True, text=True)
    if result.returncode == 0:
        modules = result.stdout
        hailo_modules = [line for line in modules.split('\n') if 'hailo' in line.lower()]
        if hailo_modules:
            print("✅ Hailo kernel modules loaded:")
            for module in hailo_modules:
                print(f"  {module}")
        else:
            print("⚠️ No Hailo kernel modules loaded")
            
except Exception as e:
    print(f"⚠️ Could not check system information: {e}")

print("\n=== Test completed ===")
print("💡 If all tests pass, Hailo YOLO should work correctly")
print("🚀 Run 'docker compose up yolo-camera-stream' to start the processor")
print("📷 Run './start_hailo_camera.sh' to start camera stream") 