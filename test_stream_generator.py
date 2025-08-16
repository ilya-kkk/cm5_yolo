#!/usr/bin/env python3
"""
Test Stream Generator
Creates fake frames for testing video streaming
"""

import cv2
import numpy as np
import time
import os

def create_test_frame(frame_number):
    """Create a test frame with frame number"""
    # Create a 640x480 image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add some visual elements
    cv2.rectangle(img, (50, 50), (590, 430), (0, 255, 0), 3)
    cv2.putText(img, f'Test Frame {frame_number}', (100, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Add timestamp
    timestamp = time.strftime("%H:%M:%S")
    cv2.putText(img, timestamp, (100, 150), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    # Add moving object
    x = int(100 + 50 * np.sin(frame_number * 0.1))
    y = int(200 + 30 * np.cos(frame_number * 0.15))
    cv2.circle(img, (x, y), 20, (0, 0, 255), -1)
    
    return img

def main():
    """Main function"""
    frame_count = 0
    
    print("Starting test stream generator...")
    print("Creating frames in /tmp/processed_frame_*.jpg")
    
    try:
        while True:
            # Create test frame
            frame = create_test_frame(frame_count)
            
            # Save frame
            filename = f"/tmp/processed_frame_{frame_count}.jpg"
            cv2.imwrite(filename, frame)
            
            print(f"Generated frame {frame_count}: {filename}")
            
            # Clean up old frames (keep last 10)
            if frame_count > 10:
                old_file = f"/tmp/processed_frame_{frame_count - 10}.jpg"
                if os.path.exists(old_file):
                    os.remove(old_file)
            
            frame_count += 1
            time.sleep(0.1)  # 10 FPS
            
    except KeyboardInterrupt:
        print("\nStopping test stream generator...")
        print(f"Generated {frame_count} frames")

if __name__ == "__main__":
    main() 