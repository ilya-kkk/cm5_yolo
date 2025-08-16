#!/usr/bin/env python3
"""
Test script for Web Service
Tests the web service functionality without requiring the full YOLO stream
"""

import requests
import time
import sys
import os

def test_web_service():
    """Test web service endpoints"""
    base_url = "http://localhost:8080"
    
    print("🧪 Testing Web Service...")
    print(f"Base URL: {base_url}")
    print("-" * 50)
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check passed: {data}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Health check error: {e}")
        return False
    
    # Test 2: Main page
    print("2. Testing main page...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Main page loaded: {len(response.text)} characters")
        else:
            print(f"   ❌ Main page failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Main page error: {e}")
        return False
    
    # Test 3: Stream info API
    print("3. Testing stream info API...")
    try:
        response = requests.get(f"{base_url}/api/stream_info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Stream info: {data}")
        else:
            print(f"   ❌ Stream info failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Stream info error: {e}")
        return False
    
    # Test 4: Video stream (should return MJPEG)
    print("4. Testing video stream...")
    try:
        response = requests.get(f"{base_url}/stream", timeout=10, stream=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'multipart/x-mixed-replace' in content_type:
                print(f"   ✅ Video stream working: {content_type}")
            else:
                print(f"   ⚠️  Video stream returned: {content_type}")
        else:
            print(f"   ❌ Video stream failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Video stream error: {e}")
        return False
    
    print("-" * 50)
    print("🎉 All tests passed! Web service is working correctly.")
    return True

def check_service_status():
    """Check if web service is running"""
    try:
        response = requests.get("http://localhost:8080/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def main():
    """Main function"""
    print("🚀 Web Service Test Script")
    print("=" * 50)
    
    # Check if service is running
    if not check_service_status():
        print("❌ Web service is not running on port 8080")
        print("Please start the web service first:")
        print("   ./start_web_service.sh")
        print("   or")
        print("   docker-compose up web-stream-service")
        sys.exit(1)
    
    # Run tests
    if test_web_service():
        print("\n🌐 Web service is ready!")
        print(f"Access your video stream at: http://localhost:8080")
        print("📱 Mobile-friendly interface available")
    else:
        print("\n❌ Web service tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 