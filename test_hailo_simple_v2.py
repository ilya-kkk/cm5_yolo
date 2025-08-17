#!/usr/bin/env python3

import sys
import os

print("🧪 Testing Hailo Platform v2...")

try:
    import hailo_platform.pyhailort.pyhailort as pyhailort
    print("✅ Hailo platform imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Hailo platform: {e}")
    sys.exit(1)

def test_device_scan():
    """Test device scanning"""
    try:
        print("\n🔍 Testing device scan...")
        
        # Try to scan for devices
        devices = pyhailort.Device.scan()
        print(f"✅ Found {len(devices)} devices")
        
        for i, device in enumerate(devices):
            print(f"  Device {i}: {device}")
            
        return True
    except Exception as e:
        print(f"❌ Device scan failed: {e}")
        return False

def test_vdevice_creation():
    """Test VDevice creation"""
    try:
        print("\n🔍 Testing VDevice creation...")
        
        # Try to create VDevice
        vdevice = pyhailort.VDevice()
        print("✅ VDevice created successfully")
        
        # Try to get device info
        try:
            info = vdevice.get_device_infos()
            print(f"✅ Device info: {info}")
        except Exception as e:
            print(f"⚠️ Could not get device info: {e}")
        
        vdevice.release()
        return True
    except Exception as e:
        print(f"❌ VDevice creation failed: {e}")
        return False

def test_hef_loading():
    """Test HEF file loading"""
    try:
        print("\n📦 Testing HEF loading...")
        
        # Check if HEF file exists
        hef_path = "yolov8n.hef"
        if not os.path.exists(hef_path):
            print(f"❌ HEF file not found: {hef_path}")
            return False
            
        print(f"✅ HEF file found: {hef_path}")
        
        # Try to load HEF
        hef = pyhailort.HEF(hef_path)
        print("✅ HEF loaded successfully")
        
        # Get network groups
        network_groups = hef.get_network_group_names()
        print(f"✅ Network groups: {network_groups}")
        
        # Get stream info
        input_streams = hef.get_input_vstream_infos()
        output_streams = hef.get_output_vstream_infos()
        print(f"✅ Input streams: {len(input_streams)}")
        print(f"✅ Output streams: {len(output_streams)}")
        
        return True
    except Exception as e:
        print(f"❌ HEF loading failed: {e}")
        return False

def test_simple_configure():
    """Test simple configuration without ConfigureParams"""
    try:
        print("\n⚙️ Testing simple configuration...")
        
        # Load HEF
        hef = pyhailort.HEF("yolov8n.hef")
        
        # Create VDevice
        vdevice = pyhailort.VDevice()
        
        # Try to configure with empty dict
        print("  Trying empty dict configuration...")
        configured_model = vdevice.configure(hef, {})
        print("✅ Configuration successful with empty dict")
        
        # Cleanup
        configured_model.release()
        vdevice.release()
        
        return True
    except Exception as e:
        print(f"❌ Simple configuration failed: {e}")
        return False

def test_configure_params():
    """Test configuration with ConfigureParams"""
    try:
        print("\n⚙️ Testing ConfigureParams configuration...")
        
        # Load HEF
        hef = pyhailort.HEF("yolov8n.hef")
        
        # Create VDevice
        vdevice = pyhailort.VDevice()
        
        # Try different interfaces
        interfaces = [
            pyhailort.HailoStreamInterface.PCIe,
            pyhailort.HailoStreamInterface.INTEGRATED,
            pyhailort.HailoStreamInterface.MIPI,
            pyhailort.HailoStreamInterface.ETH
        ]
        
        for interface in interfaces:
            try:
                print(f"  Trying interface: {interface}")
                configure_params = pyhailort.ConfigureParams.create_from_hef(hef, interface)
                configured_model = vdevice.configure(hef, configure_params)
                print(f"✅ Configuration successful with {interface}")
                
                # Cleanup
                configured_model.release()
                break
                
            except Exception as e:
                print(f"  ❌ Failed with {interface}: {e}")
                continue
        
        vdevice.release()
        return True
    except Exception as e:
        print(f"❌ ConfigureParams configuration failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Hailo Platform tests...")
    
    tests = [
        ("Device Scan", test_device_scan),
        ("VDevice Creation", test_vdevice_creation),
        ("HEF Loading", test_hef_loading),
        ("Simple Configure", test_simple_configure),
        ("ConfigureParams", test_configure_params)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n📊 Test Results:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"Total: {total}, Passed: {passed}, Failed: {total - passed}")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 