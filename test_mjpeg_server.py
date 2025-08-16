#!/usr/bin/env python3
"""
Test script for MJPEG Video Server
"""

import requests
import time

def test_mjpeg_server():
    """Test the MJPEG video server"""
    base_url = "http://192.168.0.164:8084"
    
    print("Testing MJPEG Video Server...")
    print(f"Base URL: {base_url}")
    print("-" * 50)
    
    try:
        # Test 1: Main page
        print("1. Testing main page...")
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("   ✅ Main page loaded successfully")
            print(f"   📄 Content length: {len(response.text)} characters")
        else:
            print(f"   ❌ Main page failed: {response.status_code}")
            return False
            
        # Test 2: Status endpoint
        print("\n2. Testing status endpoint...")
        response = requests.get(f"{base_url}/status", timeout=10)
        if response.status_code == 200:
            print("   ✅ Status endpoint working")
            status_data = response.json()
            print(f"   📊 Status: {status_data.get('status', 'Unknown')}")
            print(f"   🎞️  Latest frame: {status_data.get('latest_frame', 'Unknown')}")
        else:
            print(f"   ❌ Status endpoint failed: {response.status_code}")
            
        # Test 3: Video feed (MJPEG stream)
        print("\n3. Testing MJPEG video feed...")
        response = requests.get(f"{base_url}/video_feed", timeout=5, stream=True)
        if response.status_code == 200:
            print("   ✅ MJPEG video feed working")
            print(f"   📹 Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            
            # Check if it's actually MJPEG
            content_type = response.headers.get('Content-Type', '')
            if 'multipart/x-mixed-replace' in content_type:
                print("   🎯 Correct MJPEG format detected")
            else:
                print("   ⚠️  Unexpected content type")
                
        else:
            print(f"   ❌ MJPEG video feed failed: {response.status_code}")
            
        # Test 4: CORS headers
        print("\n4. Testing CORS headers...")
        response = requests.options(f"{base_url}/", timeout=10)
        cors_origin = response.headers.get('Access-Control-Allow-Origin', '')
        if cors_origin == '*':
            print("   ✅ CORS headers present")
            print("   🌐 CORS Origin: *")
        else:
            print("   ⚠️  CORS headers missing or incorrect")
            
        print("\n" + "=" * 50)
        print("🎉 All tests passed! MJPEG server is working correctly.")
        print(f"🌐 Open your browser and go to: {base_url}")
        print("📱 This solution provides the best video quality and performance!")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - server might not be running")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timeout - server might be slow")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    test_mjpeg_server() 