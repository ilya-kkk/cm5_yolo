#!/usr/bin/env python3
"""
Simple YOLO processor without Hailo dependencies
Uses OpenCV and Python for basic object detection simulation
"""

import cv2
import numpy as np
import time
import socket
import struct
import threading
import os
from collections import deque

class SimpleYOLOProcessor:
    def __init__(self):
        self.udp_port = int(os.environ.get('UDP_PORT', 5000))
        self.udp_socket = None
        self.processing_stats = {
            "fps": 0.0,
            "objects_detected": 0,
            "last_update": time.time(),
            "status": "Initialized"
        }
        self.frame_buffer = deque(maxlen=10)
        
    def start_udp_listener(self):
        """Start UDP listener for incoming camera stream"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('0.0.0.0', self.udp_port))
            print(f"🔌 UDP stream listener started on port {self.udp_port}")
            return True
        except Exception as e:
            print(f"❌ Failed to start UDP stream: {e}")
            return False
    
    def process_frame(self, frame):
        """Process frame with simulated YOLO detection"""
        try:
            # Simulate YOLO processing
            height, width = frame.shape[:2]
            
            # Create a simple bounding box (simulating detected object)
            center_x, center_y = width // 2, height // 2
            box_size = min(width, height) // 4
            
            # Draw bounding box
            cv2.rectangle(frame, 
                         (center_x - box_size//2, center_y - box_size//2),
                         (center_x + box_size//2, center_y + box_size//2),
                         (0, 255, 0), 2)
            
            # Add label
            cv2.putText(frame, "Object", 
                       (center_x - box_size//2, center_y - box_size//2 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Update statistics
            self.processing_stats["objects_detected"] += 1
            current_time = time.time()
            if current_time - self.processing_stats["last_update"] > 0:
                self.processing_stats["fps"] = 1.0 / (current_time - self.processing_stats["last_update"])
            self.processing_stats["last_update"] = current_time
            
            return frame
            
        except Exception as e:
            print(f"❌ Error processing frame: {e}")
            return frame
    
    def receive_frames(self):
        """Receive frames from UDP stream"""
        print(f"📺 Waiting for camera stream on UDP port {self.udp_port}...")
        print("💡 Send MJPEG stream to this port to start processing")
        
        while True:
            try:
                if self.udp_socket:
                    data, addr = self.udp_socket.recvfrom(65536)
                    
                    # Convert received data to frame
                    nparr = np.frombuffer(data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # Process frame
                        processed_frame = self.process_frame(frame)
                        
                        # Store in buffer
                        self.frame_buffer.append(processed_frame)
                        
                        # Print status
                        print(f"✅ Frame processed - Objects: {self.processing_stats['objects_detected']}, FPS: {self.processing_stats['fps']:.1f}")
                        
            except Exception as e:
                print(f"❌ Error receiving frame: {e}")
                time.sleep(0.1)
    
    def start_processing(self):
        """Start the YOLO processor"""
        print("🚀 Starting Simple YOLO processor...")
        print("🔧 Initializing without Hailo dependencies...")
        
        # Start UDP listener
        if not self.start_udp_listener():
            print("❌ Failed to start processor")
            return False
        
        # Start frame processing thread
        processing_thread = threading.Thread(target=self.receive_frames, daemon=True)
        processing_thread.start()
        
        print("✅ Processor started successfully")
        return True
    
    def get_stats(self):
        """Get current processing statistics"""
        return self.processing_stats.copy()

def main():
    processor = SimpleYOLOProcessor()
    
    if processor.start_processing():
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
                stats = processor.get_stats()
                print(f"📊 Status: {stats['status']}, FPS: {stats['fps']:.1f}, Objects: {stats['objects_detected']}")
        except KeyboardInterrupt:
            print("\n🛑 Shutting down processor...")
    else:
        print("❌ Failed to start processor")

if __name__ == "__main__":
    main()
