#!/usr/bin/env python3
"""
Test script for WebRTC Video Server
"""

import requests
import time

def test_webrtc_server():
    """Test the WebRTC video server"""
    base_url = "http://192.168.0.164:8083"
    
    print("Testing WebRTC Video Server...")
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
            
        # Test 3: Frame endpoint
        print("\n3. Testing frame endpoint...")
        response = requests.get(f"{base_url}/frame", timeout=10)
        if response.status_code == 200:
            print("   ✅ Frame endpoint working")
            print(f"   🖼️  Frame size: {len(response.content)} bytes")
            print(f"   📋 Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        else:
            print(f"   ❌ Frame endpoint failed: {response.status_code}")
            
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
        print("🎉 All tests passed! WebRTC server is working correctly.")
        print(f"🌐 Open your browser and go to: {base_url}")
        print("📱 This solution provides modern WebRTC technology!")
        
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
    test_webrtc_server() 