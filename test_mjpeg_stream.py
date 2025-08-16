#!/usr/bin/env python3
"""
Test MJPEG Stream
Simple test to verify MJPEG stream is working
"""

import requests
import time

def test_mjpeg_stream():
    """Test the MJPEG video stream"""
    url = "http://192.168.0.164:8084/video_feed"
    
    print(f"Testing MJPEG stream: {url}")
    print("-" * 50)
    
    try:
        # Start streaming request
        response = requests.get(url, stream=True, timeout=10)
        
        if response.status_code == 200:
            print("✅ Stream started successfully")
            print(f"📹 Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            
            # Read first few chunks
            frame_count = 0
            start_time = time.time()
            
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    frame_count += 1
                    print(f"📦 Received chunk {frame_count}: {len(chunk)} bytes")
                    
                    # Check if we got a frame boundary
                    if b'--frame' in chunk:
                        print("🎯 Frame boundary detected")
                    
                    # Stop after 5 seconds or 10 chunks
                    if frame_count >= 10 or (time.time() - start_time) > 5:
                        break
                        
            print(f"\n📊 Received {frame_count} chunks in {time.time() - start_time:.2f} seconds")
            
        else:
            print(f"❌ Stream failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_mjpeg_stream() 