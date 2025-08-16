#!/usr/bin/env python3
"""
Test script for H.264 decoding from libcamera-vid UDP stream
"""

import socket
import subprocess
import tempfile
import os
import time
from pathlib import Path

def test_udp_reception():
    """Test UDP reception from libcamera-vid"""
    print("🔍 Testing UDP reception...")
    
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('127.0.0.1', 5000))
        sock.settimeout(5.0)
        
        print("✅ UDP socket created, waiting for data...")
        
        # Receive data
        data, addr = sock.recvfrom(65536)
        
        if data:
            print(f"📦 Received {len(data)} bytes from {addr}")
            print(f"📊 First 100 bytes: {data[:100]}")
            
            # Check for H.264 start codes
            start_codes = [b'\x00\x00\x01', b'\x00\x00\x00\x01']
            found_codes = []
            
            for code in start_codes:
                if code in data:
                    found_codes.append(code)
                    count = data.count(code)
                    print(f"🎯 Found start code {code}: {count} times")
            
            if not found_codes:
                print("⚠️ No H.264 start codes found!")
                print("🔍 Raw data analysis:")
                print(f"   Data type: {type(data)}")
                print(f"   Data length: {len(data)}")
                print(f"   First bytes: {[b for b in data[:20]]}")
                print(f"   Hex: {data[:20].hex()}")
            
            return data
        else:
            print("❌ No data received")
            return None
            
    except Exception as e:
        print(f"❌ UDP test error: {e}")
        return None
    finally:
        sock.close()

def test_ffmpeg_decode(h264_data):
    """Test FFmpeg decoding with different approaches"""
    if not h264_data:
        print("❌ No H.264 data to test")
        return
    
    print("\n🔧 Testing FFmpeg decoding...")
    
    # Test 1: Basic H.264 decode
    print("📝 Test 1: Basic H.264 decode")
    try:
        with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
            temp_file.write(h264_data)
            temp_file_path = temp_file.name
        
        output_path = temp_file_path + '.jpg'
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'h264',
            '-i', temp_file_path,
            '-vframes', '1',
            '-q:v', '2',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print("✅ Basic decode successful")
            file_size = os.path.getsize(output_path)
            print(f"📊 Output file size: {file_size} bytes")
        else:
            print("❌ Basic decode failed")
            print(f"FFmpeg stderr: {result.stderr.decode()}")
        
        # Cleanup
        try:
            os.unlink(temp_file_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
        except:
            pass
            
    except Exception as e:
        print(f"❌ Test 1 error: {e}")
    
    # Test 2: With stream parameters
    print("\n📝 Test 2: With stream parameters")
    try:
        with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
            temp_file.write(h264_data)
            temp_file_path = temp_file.name
        
        output_path = temp_file_path + '.jpg'
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'h264',
            '-i', temp_file_path,
            '-vframes', '1',
            '-q:v', '2',
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=640:480',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print("✅ Parameterized decode successful")
            file_size = os.path.getsize(output_path)
            print(f"📊 Output file size: {file_size} bytes")
        else:
            print("❌ Parameterized decode failed")
            print(f"FFmpeg stderr: {result.stderr.decode()}")
        
        # Cleanup
        try:
            os.unlink(temp_file_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
        except:
            pass
            
    except Exception as e:
        print(f"❌ Test 2 error: {e}")
    
    # Test 3: Raw video output
    print("\n📝 Test 3: Raw video output")
    try:
        with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
            temp_file.write(h264_data)
            temp_file_path = temp_file.name
        
        output_path = temp_file_path + '.raw'
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'h264',
            '-i', temp_file_path,
            '-vframes', '1',
            '-f', 'rawvideo',
            '-pix_fmt', 'rgb24',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print("✅ Raw decode successful")
            file_size = os.path.getsize(output_path)
            print(f"📊 Output file size: {file_size} bytes")
            
            # Check if size matches expected frame size
            expected_size = 640 * 480 * 3  # RGB24
            if file_size == expected_size:
                print("✅ Frame size matches expected (640x480 RGB)")
            else:
                print(f"⚠️ Frame size mismatch: expected {expected_size}, got {file_size}")
        else:
            print("❌ Raw decode failed")
            print(f"FFmpeg stderr: {result.stderr.decode()}")
        
        # Cleanup
        try:
            os.unlink(temp_file_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
        except:
            pass
            
    except Exception as e:
        print(f"❌ Test 3 error: {e}")

def test_gstreamer_decode(h264_data):
    """Test GStreamer decoding as alternative to FFmpeg"""
    if not h264_data:
        print("❌ No H.264 data to test")
        return
    
    print("\n🔧 Testing GStreamer decoding...")
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
            temp_file.write(h264_data)
            temp_file_path = temp_file.name
        
        output_path = temp_file_path + '.jpg'
        
        # GStreamer pipeline
        pipeline = f"""
        filesrc location={temp_file_path} ! 
        h264parse ! 
        avdec_h264 ! 
        videoconvert ! 
        jpegenc ! 
        multifilesink location={output_path}
        """
        
        cmd = ['gst-launch-1.0', '-q', pipeline]
        
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print("✅ GStreamer decode successful")
            file_size = os.path.getsize(output_path)
            print(f"📊 Output file size: {file_size} bytes")
        else:
            print("❌ GStreamer decode failed")
            print(f"GStreamer stderr: {result.stderr.decode()}")
        
        # Cleanup
        try:
            os.unlink(temp_file_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
        except:
            pass
            
    except Exception as e:
        print(f"❌ GStreamer test error: {e}")

def main():
    """Main test function"""
    print("🚀 H.264 Decoding Test Script")
    print("=" * 40)
    
    # Test UDP reception
    h264_data = test_udp_reception()
    
    if h264_data:
        # Test different decoding approaches
        test_ffmpeg_decode(h264_data)
        test_gstreamer_decode(h264_data)
        
        print("\n📋 Summary:")
        print("✅ UDP reception working")
        print("🔧 Tested multiple decoding approaches")
        print("📊 Check output above for best method")
    else:
        print("\n❌ No H.264 data received")
        print("💡 Make sure libcamera-vid is running:")
        print("   libcamera-vid -t 0 --codec h264 --width 640 --height 480 --framerate 30 --inline -o udp://127.0.0.1:5000")

if __name__ == "__main__":
    main() 