#!/usr/bin/env python3
"""
Simple Hailo test script
"""

import sys
import os

# Add system Python path
sys.path.insert(0, '/usr/lib/python3/dist-packages')

def test_hailo_import():
    """Test Hailo imports"""
    print("🔍 Testing Hailo imports...")
    
    try:
        import hailo_platform
        print("✅ hailo_platform imported successfully")
        
        # Check what's available
        print(f"📋 hailo_platform attributes: {dir(hailo_platform)}")
        
        # Try to access Hailo device
        if hasattr(hailo_platform, 'HailoDevice'):
            print("✅ HailoDevice class found")
            try:
                devices = hailo_platform.HailoDevice.scan()
                print(f"✅ Hailo devices found: {len(devices)}")
                for device in devices:
                    print(f"  - {device}")
            except Exception as e:
                print(f"⚠️ Error scanning devices: {e}")
        else:
            print("⚠️ HailoDevice class not found")
            
    except ImportError as e:
        print(f"❌ hailo_platform import failed: {e}")
    
    try:
        import hailo_platform.drivers.hailort.pyhailort as pyhailort
        print("✅ pyhailort imported successfully")
        print(f"📋 pyhailort attributes: {dir(pyhailort)}")
    except ImportError as e:
        print(f"❌ pyhailort import failed: {e}")

def test_hailort_cli():
    """Test HailoRT CLI"""
    print("\n🚀 Testing HailoRT CLI...")
    
    import subprocess
    
    try:
        result = subprocess.run(['hailortcli', 'scan'], capture_output=True, text=True, timeout=10)
        print(f"hailortcli scan output: {result.stdout}")
        if result.stderr:
            print(f"hailortcli scan errors: {result.stderr}")
    except Exception as e:
        print(f"❌ hailortcli scan failed: {e}")

def main():
    """Main function"""
    print("🎯 Simple Hailo Test")
    print("=" * 50)
    
    test_hailo_import()
    test_hailort_cli()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed")

if __name__ == "__main__":
    main() 