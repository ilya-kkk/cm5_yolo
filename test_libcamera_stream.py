#!/usr/bin/env python3
"""
Test libcamera streaming on CM5
"""

import subprocess
import time
import signal
import sys

def test_libcamera_stream():
    """Test libcamera-vid streaming"""
    print("🧪 Testing libcamera-vid streaming...")
    
    # Test command
    cmd = [
        'libcamera-vid',
        '-t', '10000',  # 10 seconds
        '--codec', 'h264',
        '--width', '640',
        '--height', '480',
        '--framerate', '30',
        '--inline',
        '-o', 'udp://127.0.0.1:5000'
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Start libcamera-vid
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("✅ libcamera-vid started successfully")
        print("📡 Streaming to UDP port 5000...")
        print("⏱️  Will run for 10 seconds...")
        
        # Wait for process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            print("✅ libcamera-vid completed successfully")
        else:
            print(f"❌ libcamera-vid failed with return code: {process.returncode}")
            print(f"Stderr: {stderr.decode()}")
            
    except Exception as e:
        print(f"❌ Error running libcamera-vid: {e}")

def test_libcamera_devices():
    """Test libcamera device detection"""
    print("\n🔍 Testing libcamera device detection...")
    
    try:
        # List cameras
        result = subprocess.run(['libcamera-still', '--list-cameras'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ libcamera-still --list-cameras:")
            print(result.stdout)
        else:
            print(f"❌ libcamera-still failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error listing cameras: {e}")

def test_camera_access():
    """Test basic camera access"""
    print("\n📹 Testing basic camera access...")
    
    try:
        # Try to capture a single image
        result = subprocess.run([
            'libcamera-still',
            '--width', '640',
            '--height', '480',
            '--output', '/tmp/test_image.jpg',
            '--timeout', '5000'
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("✅ Successfully captured test image")
            print("📁 Saved to /tmp/test_image.jpg")
        else:
            print(f"❌ Failed to capture image: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error capturing image: {e}")

if __name__ == "__main__":
    print("🚀 CM5 Camera Test Suite")
    print("=" * 50)
    
    # Test device detection
    test_libcamera_devices()
    
    # Test basic camera access
    test_camera_access()
    
    # Test streaming
    test_libcamera_stream()
    
    print("\n✅ Test suite completed!") 