#!/usr/bin/env python3
"""
Test Camera Script
Simple script to test CSI camera functionality
"""

import cv2
import time
import sys

def test_camera(camera_index=0, width=1920, height=1080, fps=30):
    """Test camera functionality"""
    print(f"Testing camera {camera_index} at {width}x{height} @ {fps}fps")
    
    # Try different camera backends
    camera_backends = [
        f"libcamera://{camera_index}",
        f"v4l2:///dev/video{camera_index}",
        f"/dev/video{camera_index}"
    ]
    
    camera = None
    backend_used = None
    
    for backend in camera_backends:
        try:
            print(f"Trying backend: {backend}")
            camera = cv2.VideoCapture(backend)
            
            if camera.isOpened():
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                camera.set(cv2.CAP_PROP_FPS, fps)
                
                # Test frame capture
                ret, frame = camera.read()
                if ret:
                    print(f"✓ Camera working with {backend}")
                    print(f"  Frame shape: {frame.shape}")
                    print(f"  Frame type: {frame.dtype}")
                    backend_used = backend
                    break
                else:
                    print(f"✗ Failed to capture frame from {backend}")
                    camera.release()
            else:
                print(f"✗ Failed to open camera with {backend}")
                
        except Exception as e:
            print(f"✗ Error with {backend}: {e}")
            if camera:
                camera.release()
    
    if not camera or not camera.isOpened():
        print("❌ All camera backends failed")
        return False
    
    print(f"\nCamera test successful!")
    print(f"Backend: {backend_used}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps}")
    
    # Display camera properties
    print(f"\nCamera properties:")
    print(f"  CAP_PROP_FRAME_WIDTH: {camera.get(cv2.CAP_PROP_FRAME_WIDTH)}")
    print(f"  CAP_PROP_FRAME_HEIGHT: {camera.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    print(f"  CAP_PROP_FPS: {camera.get(cv2.CAP_PROP_FPS)}")
    print(f"  CAP_PROP_FOURCC: {camera.get(cv2.CAP_PROP_FOURCC)}")
    
    # Test continuous capture
    print(f"\nTesting continuous capture (5 seconds)...")
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < 5:
        ret, frame = camera.read()
        if ret:
            frame_count += 1
            # Display frame
            cv2.imshow('Camera Test', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("Failed to capture frame during continuous test")
            break
    
    actual_fps = frame_count / 5
    print(f"Captured {frame_count} frames in 5 seconds")
    print(f"Actual FPS: {actual_fps:.1f}")
    
    # Clean up
    camera.release()
    cv2.destroyAllWindows()
    
    return True

def main():
    """Main function"""
    if len(sys.argv) > 1:
        camera_index = int(sys.argv[1])
    else:
        camera_index = 0
    
    print("CSI Camera Test Script")
    print("=" * 50)
    
    success = test_camera(camera_index)
    
    if success:
        print("\n✅ Camera test completed successfully!")
        print("Camera is ready for YOLO processing")
    else:
        print("\n❌ Camera test failed!")
        print("Please check camera connection and permissions")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 