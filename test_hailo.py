#!/usr/bin/env python3
"""
Test Hailo device access and initialization
"""

import os
import subprocess
import sys

def check_hailo_devices():
    """Check for Hailo devices"""
    print("🔍 Checking Hailo devices...")
    
    # Check PCIe
    try:
        result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            hailo_lines = [line for line in result.stdout.split('\n') if 'hailo' in line.lower()]
            if hailo_lines:
                print(f"✅ Hailo PCIe found: {hailo_lines[0]}")
            else:
                print("❌ No Hailo PCIe found")
        else:
            print(f"❌ lspci failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Error running lspci: {e}")
    
    # Check kernel modules
    try:
        result = subprocess.run(['lsmod'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            hailo_modules = [line for line in result.stdout.split('\n') if 'hailo' in line.lower()]
            if hailo_modules:
                print(f"✅ Hailo kernel modules: {hailo_modules}")
            else:
                print("❌ No Hailo kernel modules")
        else:
            print(f"❌ lsmod failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Error running lsmod: {e}")
    
    # Check device files
    try:
        result = subprocess.run(['ls', '-la', '/dev'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            hailo_devices = [line for line in result.stdout.split('\n') if 'hailo' in line.lower()]
            if hailo_devices:
                print(f"✅ Hailo device files: {hailo_devices}")
            else:
                print("❌ No Hailo device files")
        else:
            print(f"❌ ls /dev failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Error checking /dev: {e}")

def test_hailort():
    """Test HailoRT access"""
    print("\n🚀 Testing HailoRT...")
    
    # Try hailortcli scan
    try:
        result = subprocess.run(['hailortcli', 'scan'], capture_output=True, text=True, timeout=10)
        print(f"hailortcli scan output: {result.stdout}")
        if result.stderr:
            print(f"hailortcli scan errors: {result.stderr}")
    except Exception as e:
        print(f"❌ hailortcli scan failed: {e}")
    
    # Try hailortcli list-devices
    try:
        result = subprocess.run(['hailortcli', 'list-devices'], capture_output=True, text=True, timeout=10)
        print(f"hailortcli list-devices output: {result.stdout}")
        if result.stderr:
            print(f"hailortcli list-devices errors: {result.stderr}")
    except Exception as e:
        print(f"❌ hailortcli list-devices failed: {e}")

def test_python_hailo():
    """Test Python Hailo imports"""
    print("\n🐍 Testing Python Hailo imports...")
    
    try:
        import hailo_platform
        print("✅ hailo_platform imported successfully")
        
        # Try to get Hailo device
        try:
            devices = hailo_platform.HailoDevice.scan()
            print(f"✅ Hailo devices found: {len(devices)}")
            for device in devices:
                print(f"  - {device}")
        except Exception as e:
            print(f"❌ Error scanning Hailo devices: {e}")
            
    except ImportError as e:
        print(f"❌ hailo_platform import failed: {e}")
    
    try:
        import hailo
        print("✅ hailo imported successfully")
    except ImportError as e:
        print(f"❌ hailo import failed: {e}")

def main():
    """Main function"""
    print("🎯 Hailo Device Test Script")
    print("=" * 50)
    
    check_hailo_devices()
    test_hailort()
    test_python_hailo()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed")

if __name__ == "__main__":
    main() 