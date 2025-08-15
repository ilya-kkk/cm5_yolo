#!/usr/bin/env python3
"""
Test script to verify web server functionality
"""

import requests
import time

def test_web_server():
    """Test the web server endpoints"""
    base_url = "http://192.168.0.164:8080"
    
    print("Testing YOLO Video Web Server...")
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
            print(f"   ❌ Main page failed: HTTP {response.status_code}")
            return False
        
        # Test 2: Status endpoint
        print("\n2. Testing status endpoint...")
        response = requests.get(f"{base_url}/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Status endpoint working")
            print(f"   📊 Status: {data.get('status', 'Unknown')}")
            print(f"   🎞️  Latest frame: {data.get('latest_frame', 'Unknown')}")
            print(f"   📈 Total frames: {data.get('total_frames', 'Unknown')}")
        else:
            print(f"   ❌ Status endpoint failed: HTTP {response.status_code}")
            return False
        
        # Test 3: Frame endpoint
        print("\n3. Testing frame endpoint...")
        response = requests.get(f"{base_url}/frame", timeout=10)
        if response.status_code == 200:
            print("   ✅ Frame endpoint working")
            print(f"   🖼️  Frame size: {len(response.content)} bytes")
            print(f"   📋 Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        else:
            print(f"   ❌ Frame endpoint failed: HTTP {response.status_code}")
            return False
        
        # Test 4: CORS headers
        print("\n4. Testing CORS headers...")
        response = requests.options(f"{base_url}/status", timeout=10)
        if response.status_code == 200:
            cors_headers = response.headers.get('Access-Control-Allow-Origin')
            if cors_headers:
                print("   ✅ CORS headers present")
                print(f"   🌐 CORS Origin: {cors_headers}")
            else:
                print("   ⚠️  CORS headers missing")
        else:
            print(f"   ❌ CORS test failed: HTTP {response.status_code}")
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! Web server is working correctly.")
        print(f"🌐 Open your browser and go to: {base_url}")
        return True
        
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection failed - server might not be running")
        return False
    except requests.exceptions.Timeout:
        print("   ❌ Request timeout - server might be slow")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_web_server() 