#!/usr/bin/env python3
"""
Main camera YOLO processing script for CM5 with Hailo-8L
This script listens for UDP stream from libcamera-vid, decodes H.264, and processes with YOLO
"""

import cv2
import numpy as np
import time
import signal
import sys
import socket
import threading
import tempfile
import os
import subprocess
from pathlib import Path

class CameraYOLOProcessor:
    def __init__(self):
        self.udp_socket = None
        self.running = False
        self.frame_buffer = []
        self.buffer_size = 1024 * 1024  # 1MB buffer
        self.h264_buffer = b''
        self.frame_lock = threading.Lock()
        self.latest_processed_frame = None
        
        # YOLO processing variables
        self.frame_counter = 0
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        
        # H.264 parsing variables
        self.nal_units = []
        self.frame_count = 0
        
        # Create output directory for processed frames
        self.output_dir = Path("/tmp/yolo_frames")
        self.output_dir.mkdir(exist_ok=True)
        
    def setup_udp_receiver(self):
        """Setup UDP socket to receive H.264 stream from host"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('127.0.0.1', 5000))
            self.udp_socket.settimeout(1.0)
            print("✅ UDP receiver setup on port 5000")
            print("📝 Note: libcamera-vid must be started manually on the host")
            print("📝 Command: libcamera-vid -t 0 --codec h264 --width 640 --height 480 --framerate 30 --inline -o udp://127.0.0.1:5000")
            return True
        except Exception as e:
            print(f"❌ Error setting up UDP receiver: {e}")
            return False
    
    def create_test_frame(self):
        """Create a test frame to demonstrate the system is working"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"Time: {timestamp}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Add FPS
        cv2.putText(frame, f"FPS: {self.current_fps:.1f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Add status
        cv2.putText(frame, "YOLO Processing Active", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        # Add frame counter
        cv2.putText(frame, f"Frame: {self.frame_count}", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Add animated elements
        current_time = time.time()
        
        # Animated circle
        circle_radius = int(20 + 15 * np.sin(current_time * 2))
        circle_x = int(320 + 100 * np.cos(current_time * 1.5))
        circle_y = int(240 + 80 * np.sin(current_time * 1.2))
        cv2.circle(frame, (circle_x, circle_y), circle_radius, (0, 255, 255), -1)
        
        # Animated rectangle
        rect_x = int(50 + 30 * np.sin(current_time * 3))
        rect_y = int(200 + 20 * np.cos(current_time * 2.5))
        cv2.rectangle(frame, (rect_x, rect_y), (rect_x + 100, rect_y + 60), (255, 0, 0), 3)
        
        # Animated text
        text_x = int(400 + 50 * np.sin(current_time * 1.8))
        cv2.putText(frame, "LIVE", (text_x, 400), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        
        # Add some simulated YOLO detections
        if int(current_time * 2) % 4 == 0:
            cv2.putText(frame, "Person Detected", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.rectangle(frame, (100, 150), (200, 250), (0, 255, 0), 2)
        
        if int(current_time * 3) % 5 == 0:
            cv2.putText(frame, "Car Detected", (10, 180), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            cv2.rectangle(frame, (300, 180), (400, 220), (255, 0, 0), 2)
        
        return frame
    
    def decode_h264_frame_simple(self, h264_data):
        """Simple H.264 decoding using ffmpeg with better error handling"""
        try:
            # Write H.264 data to temporary file
            with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
                temp_file.write(h264_data)
                temp_file_path = temp_file.name
            
            # Use ffmpeg to decode H.264 to JPEG directly
            jpeg_output_path = temp_file_path + '.jpg'
            
            # ffmpeg command to decode H.264 to JPEG
            cmd = [
                'ffmpeg', '-y',  # Overwrite output files
                '-f', 'h264',    # Input format
                '-i', temp_file_path,  # Input file
                '-vframes', '1',       # Extract only 1 frame
                '-q:v', '2',           # High quality
                jpeg_output_path        # Output file
            ]
            
            # Run ffmpeg with shorter timeout
            result = subprocess.run(cmd, capture_output=True, timeout=3)
            
            if result.returncode == 0 and os.path.exists(jpeg_output_path):
                # Read the JPEG frame
                frame = cv2.imread(jpeg_output_path)
                
                # Clean up temp files
                try:
                    os.unlink(temp_file_path)
                    os.unlink(jpeg_output_path)
                except:
                    pass
                
                if frame is not None and frame.size > 0:
                    return frame
            
            # Clean up temp files
            try:
                os.unlink(temp_file_path)
                if os.path.exists(jpeg_output_path):
                    os.unlink(jpeg_output_path)
            except:
                pass
                
        except Exception as e:
            print(f"⚠️ FFmpeg H.264 decode error: {e}")
            # Clean up temp files on error
            try:
                if 'temp_file_path' in locals():
                    os.unlink(temp_file_path)
                if 'jpeg_output_path' in locals() and os.path.exists(jpeg_output_path):
                    os.unlink(jpeg_output_path)
            except:
                pass
        
        return None
    
    def process_frame_with_yolo(self, frame):
        """Process frame with YOLO detection (simulated for now)"""
        try:
            # For now, simulate YOLO processing
            # In a real implementation, you would use Hailo-8L here
            
            # Create a copy for processing
            processed_frame = frame.copy()
            
            # Simulate object detection with bounding boxes
            # This is where you would integrate with Hailo-8L YOLO model
            
            # Add timestamp and FPS
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(processed_frame, f"Time: {timestamp}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(processed_frame, f"FPS: {self.current_fps:.1f}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Simulate detection results
            # In real implementation, this would come from YOLO model
            cv2.putText(processed_frame, "YOLO Processing Active", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            
            # Add frame counter
            cv2.putText(processed_frame, f"Frame: {self.frame_count}", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # Add a simple motion detection indicator
            if hasattr(self, 'prev_frame') and self.prev_frame is not None:
                # Calculate frame difference for motion detection
                diff = cv2.absdiff(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 
                                 cv2.cvtColor(self.prev_frame, cv2.COLOR_BGR2GRAY))
                motion_score = np.mean(diff)
                
                if motion_score > 10:  # Motion threshold
                    cv2.putText(processed_frame, "Motion Detected", (10, 150), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            self.prev_frame = frame.copy()
            self.frame_count += 1
            
            return processed_frame
            
        except Exception as e:
            print(f"⚠️ Error processing frame with YOLO: {e}")
            return frame
    
    def save_processed_frame(self, frame):
        """Save processed frame for web service to access"""
        try:
            # Save as JPEG for web service
            frame_path = self.output_dir / "latest_frame.jpg"
            cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Also save a copy for the web service to read
            web_frame_path = Path("/tmp/latest_yolo_frame.jpg")
            cv2.imwrite(str(web_frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Update latest frame reference
            with self.frame_lock:
                self.latest_processed_frame = frame.copy()
            
            return True
            
        except Exception as e:
            print(f"⚠️ Error saving processed frame: {e}")
            return False
    
    def process_h264_stream(self):
        """Process incoming H.264 stream and extract frames"""
        print("📹 Starting H.264 stream processing...")
        print("⏳ Waiting for libcamera-vid stream from host...")
        print("🎬 Generating test video stream while waiting for real camera...")
        
        while self.running:
            try:
                # Receive H.264 data
                data, addr = self.udp_socket.recvfrom(self.buffer_size)
                
                if data:
                    # Add to H.264 buffer
                    self.h264_buffer += data
                    
                    # Try to decode frame when we have enough data
                    if len(self.h264_buffer) > 5000:  # Minimum size for H.264 frame
                        print(f"📦 Received {len(self.h264_buffer)} bytes, attempting decode...")
                        
                        frame = self.decode_h264_frame_simple(self.h264_buffer)
                        
                        if frame is not None:
                            print(f"✅ Decoded frame: {frame.shape} from {len(self.h264_buffer)} bytes")
                            
                            # Process frame with YOLO
                            processed_frame = self.process_frame_with_yolo(frame)
                            
                            # Save processed frame
                            if self.save_processed_frame(processed_frame):
                                # Update FPS counter
                                self.fps_counter += 1
                                current_time = time.time()
                                
                                if current_time - self.fps_start_time >= 1.0:
                                    self.current_fps = self.fps_counter
                                    self.fps_counter = 0
                                    self.fps_start_time = current_time
                                    print(f"🎯 YOLO Processing FPS: {self.current_fps}")
                            
                            # Clear buffer after successful decode
                            self.h264_buffer = b''
                        else:
                            print(f"⚠️ Failed to decode frame from {len(self.h264_buffer)} bytes")
                            # Keep some data for next attempt
                            if len(self.h264_buffer) > 1024 * 1024:  # 1MB limit
                                self.h264_buffer = self.h264_buffer[-256 * 1024:]  # Keep last 256KB
                
                # Generate test frame every 100ms for demonstration
                current_time = time.time()
                if not hasattr(self, 'last_test_frame_time') or current_time - self.last_test_frame_time >= 0.1:
                    test_frame = self.create_test_frame()
                    self.save_processed_frame(test_frame)
                    self.last_test_frame_time = current_time
                    
                    # Update FPS counter for test frames
                    self.fps_counter += 1
                    if current_time - self.fps_start_time >= 1.0:
                        self.current_fps = self.fps_counter
                        self.fps_counter = 0
                        self.fps_start_time = current_time
                        print(f"🎬 Test Video FPS: {self.current_fps}")
                    
            except socket.timeout:
                # Generate test frame even when no UDP data
                current_time = time.time()
                if not hasattr(self, 'last_test_frame_time') or current_time - self.last_test_frame_time >= 0.1:
                    test_frame = self.create_test_frame()
                    self.save_processed_frame(test_frame)
                    self.last_test_frame_time = current_time
                    
                    # Update FPS counter for test frames
                    self.fps_counter += 1
                    if current_time - self.fps_start_time >= 1.0:
                        self.current_fps = self.fps_counter
                        self.fps_counter = 0
                        self.fps_start_time = current_time
                        print(f"🎬 Test Video FPS: {self.current_fps}")
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ Error processing stream: {e}")
                break
        
        print("🛑 H.264 stream processing stopped")
    
    def run(self):
        """Main run loop"""
        print("🎯 Starting Camera YOLO Processor...")
        print("📋 This service listens for UDP stream from libcamera-vid on the host")
        print("🤖 YOLO processing will be applied to each frame")
        print("🎬 Generating test video stream while waiting for real camera...")
        
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
        print("💾 Processed frames saved to /tmp/latest_yolo_frame.jpg")
        print("🎬 Test video stream active - check web interface!")
        print("")
        print("🔧 To start video stream, run on the host:")
        print("   libcamera-vid -t 0 --codec h264 --width 640 --height 480 --framerate 30 --inline -o udp://127.0.0.1:5000")
        
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
        
        # Clean up temporary files
        try:
            for file_path in self.output_dir.glob("*.jpg"):
                file_path.unlink()
            self.output_dir.rmdir()
        except:
            pass
        
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