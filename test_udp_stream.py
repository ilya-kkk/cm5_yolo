#!/usr/bin/env python3
"""
Simple UDP stream test for camera
"""

import cv2
import numpy as np
import subprocess
import time
import signal
import sys
import os

class UDPStreamTest:
    def __init__(self, camera_index=0, width=1920, height=1080, fps=30):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.running = False
        self.gst_process = None
        
    def start_camera(self):
        """Start camera capture"""
        try:
            camera_device = f"/dev/video{self.camera_index}"
            if os.path.exists(camera_device):
                self.camera = cv2.VideoCapture(camera_device)
            else:
                self.camera = cv2.VideoCapture(f"libcamera://{self.camera_index}")
            
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            if not self.camera.isOpened():
                print(f"Failed to open camera {self.camera_index}")
                return False
                
            print(f"Camera started: {self.width}x{self.height} @ {self.fps}fps")
            return True
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def start_gstreamer_stream(self):
        """Start GStreamer UDP stream"""
        try:
            # GStreamer pipeline for UDP streaming
            gst_cmd = [
                'gst-launch-1.0',
                '-v',
                'v4l2src', f'device=/dev/video{self.camera_index}',
                '!', 'video/x-raw,width=1920,height=1080,framerate=30/1',
                '!', 'videoconvert',
                '!', 'x264enc', 'tune=zerolatency', 'speed-preset=ultrafast',
                '!', 'h264parse',
                '!', 'rtph264pay', 'config-interval=1',
                '!', 'udpsink', 'host=0.0.0.0', 'port=5000'
            ]
            
            print(f"Starting GStreamer: {' '.join(gst_cmd)}")
            
            # Start GStreamer process
            self.gst_process = subprocess.Popen(
                gst_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            print("GStreamer UDP stream started on port 5000")
            return True
            
        except Exception as e:
            print(f"Error starting GStreamer: {e}")
            return False
    
    def start(self):
        """Start the stream"""
        if not self.start_camera():
            return False
        
        if not self.start_gstreamer_stream():
            return False
        
        self.running = True
        print("UDP stream test started successfully")
        return True
    
    def stop(self):
        """Stop the stream"""
        self.running = False
        
        # Stop camera
        if hasattr(self, 'camera') and self.camera.isOpened():
            self.camera.release()
        
        # Stop GStreamer process
        if self.gst_process:
            self.gst_process.terminate()
            self.gst_process.wait()
        
        print("UDP stream test stopped")

def signal_handler(sig, frame):
    """Handle Ctrl+C signal"""
    print("\nStopping...")
    if hasattr(signal_handler, 'stream'):
        signal_handler.stream.stop()
    sys.exit(0)

def main():
    """Main function"""
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize stream
    stream = UDPStreamTest(
        camera_index=0,
        width=1920,
        height=1080,
        fps=30
    )
    
    # Store reference for signal handler
    signal_handler.stream = stream
    
    try:
        # Start stream
        if stream.start():
            print("Stream started successfully. Press Ctrl+C to stop.")
            
            # Keep main thread alive
            while True:
                time.sleep(1)
        else:
            print("Failed to start stream")
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        stream.stop()

if __name__ == "__main__":
    main() 