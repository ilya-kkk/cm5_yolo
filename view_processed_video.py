#!/usr/bin/env python3
"""
Simple script to view processed video frames in real-time
"""

import cv2
import os
import time
import glob
from pathlib import Path

def view_processed_frames():
    """View processed video frames in real-time"""
    print("Starting processed video viewer...")
    print("Press 'q' to quit, 's' to save current frame")
    
    last_frame_num = -1
    
    while True:
        try:
            # Find the latest processed frame
            frame_files = glob.glob("/tmp/processed_frame_*.jpg")
            if not frame_files:
                print("No processed frames found, waiting...")
                time.sleep(0.1)
                continue
            
            # Get the latest frame by number
            frame_numbers = []
            for f in frame_files:
                try:
                    num = int(f.split('_')[-1].split('.')[0])
                    frame_numbers.append(num)
                except:
                    continue
            
            if not frame_numbers:
                time.sleep(0.1)
                continue
            
            latest_num = max(frame_numbers)
            
            if latest_num > last_frame_num:
                # Read and display the latest frame
                latest_frame_path = f"/tmp/processed_frame_{latest_num}.jpg"
                
                if os.path.exists(latest_frame_path):
                    frame = cv2.imread(latest_frame_path)
                    if frame is not None:
                        # Resize for better viewing
                        height, width = frame.shape[:2]
                        if width > 1280:
                            scale = 1280 / width
                            new_width = int(width * scale)
                            new_height = int(height * scale)
                            frame = cv2.resize(frame, (new_width, new_height))
                        
                        # Add frame info
                        cv2.putText(frame, f"Frame: {latest_num}", (10, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        cv2.putText(frame, f"Time: {time.strftime('%H:%M:%S')}", (10, 70), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        
                        cv2.imshow('Processed YOLO Video', frame)
                        last_frame_num = latest_num
                        
                        print(f"Displaying frame {latest_num}")
                
                # Clean up old frames to save space
                for f in frame_files:
                    try:
                        num = int(f.split('_')[-1].split('.')[0])
                        if num < latest_num - 100:  # Keep only last 100 frames
                            os.remove(f)
                    except:
                        pass
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save current frame
                if last_frame_num >= 0:
                    save_path = f"processed_frame_{last_frame_num}_saved.jpg"
                    cv2.imwrite(save_path, frame)
                    print(f"Saved frame to {save_path}")
            
            time.sleep(0.033)  # ~30 FPS
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(0.1)
    
    cv2.destroyAllWindows()
    print("Video viewer stopped")

if __name__ == "__main__":
    view_processed_frames() 