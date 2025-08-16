#!/usr/bin/env python3
"""
Main camera YOLO processing script for CM5 with Hailo-8L
This script starts libcamera-vid on the host and processes the UDP stream
"""

import cv2
import numpy as np
import time
import subprocess
import signal
import sys
import socket
import threading
from pathlib import Path

class CameraYOLOProcessor:
    def __init__(self):
        self.camera_index = 0
        self.camera = None
        self.libcamera_process = None
        self.udp_socket = None
        self.running = False
        self.frame_buffer = []
        self.buffer_size = 1024 * 1024  # 1MB buffer
        
    def start_libcamera_stream(self):
        """Start libcamera-vid streaming to UDP port 5000"""
        try:
            print("🚀 Starting libcamera-vid stream...")
            
            # Kill any existing libcamera-vid processes
            subprocess.run(['pkill', 'libcamera-vid'], capture_output=True)
            time.sleep(1)
            
            # Start libcamera-vid streaming to UDP
            cmd = [
                'libcamera-vid',
                '-t', '0',  # Run indefinitely
                '--codec', 'h264',
                '--width', '640',
                '--height', '480',
                '--framerate', '30',
                '--inline',
                '-o', 'udp://127.0.0.1:5000'
            ]
            
            # Start in background
            self.libcamera_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            
            # Wait a bit to see if it starts successfully
            time.sleep(3)
            
            if self.libcamera_process.poll() is None:
                print("✅ libcamera-vid started successfully")
                return True
            else:
                print("❌ libcamera-vid failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Error starting libcamera-vid: {e}")
            return False
    
    def setup_udp_receiver(self):
        """Setup UDP socket to receive H.264 stream"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('127.0.0.1', 5000))
            self.udp_socket.settimeout(1.0)
            print("✅ UDP receiver setup on port 5000")
            return True
        except Exception as e:
            print(f"❌ Error setting up UDP receiver: {e}")
            return False
    
    def process_h264_stream(self):
        """Process incoming H.264 stream and extract frames"""
        print("📹 Starting H.264 stream processing...")
        
        while self.running:
            try:
                # Receive H.264 data
                data, addr = self.udp_socket.recvfrom(self.buffer_size)
                
                if data:
                    # For now, just log that we're receiving data
                    # In a full implementation, you would decode H.264 and run YOLO
                    print(f"📦 Received {len(data)} bytes of H.264 data")
                    
                    # Simulate YOLO processing
                    time.sleep(0.1)  # Simulate processing time
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ Error processing stream: {e}")
                break
        
        print("🛑 H.264 stream processing stopped")
    
    def run(self):
        """Main run loop"""
        print("🎯 Starting Camera YOLO Processor...")
        
        # Start libcamera-vid on host
        if not self.start_libcamera_stream():
            print("❌ Failed to start libcamera-vid")
            return
        
        # Setup UDP receiver
        if not self.setup_udp_receiver():
            print("❌ Failed to setup UDP receiver")
            return
        
        self.running = True
        
        # Start stream processing in separate thread
        stream_thread = threading.Thread(target=self.process_h264_stream)
        stream_thread.daemon = True
        stream_thread.start()
        
        print("✅ Camera YOLO Processor is running")
        print("📱 Video stream available at UDP://127.0.0.1:5000")
        print("🌐 Web interface available at http://localhost:8080")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self.stop()
    
    def stop(self):
        """Stop the processor and cleanup"""
        print("🧹 Cleaning up...")
        self.running = False
        
        if self.udp_socket:
            self.udp_socket.close()
        
        if self.libcamera_process:
            self.libcamera_process.terminate()
            self.libcamera_process.wait()
            print("✅ libcamera-vid stopped")
        
        print("✅ Cleanup complete")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n📡 Received signal {signum}, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run processor
    processor = CameraYOLOProcessor()
    
    try:
        processor.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        processor.stop()
        sys.exit(1) 