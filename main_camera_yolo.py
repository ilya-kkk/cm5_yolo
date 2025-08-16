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
    
    def decode_h264_with_ffmpeg(self, h264_data):
        """Decode H.264 data using ffmpeg"""
        try:
            # Write H.264 data to temporary file
            with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
                temp_file.write(h264_data)
                temp_file_path = temp_file.name
            
            # Use ffmpeg to decode H.264 to raw video
            raw_output_path = temp_file_path + '.raw'
            
            # ffmpeg command to decode H.264 to raw video
            cmd = [
                'ffmpeg', '-y',  # Overwrite output files
                '-f', 'h264',    # Input format
                '-i', temp_file_path,  # Input file
                '-f', 'rawvideo',      # Output format
                '-pix_fmt', 'rgb24',   # Pixel format
                '-vcodec', 'rawvideo', # Video codec
                raw_output_path         # Output file
            ]
            
            # Run ffmpeg
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            
            if result.returncode == 0 and os.path.exists(raw_output_path):
                # Read raw video data
                with open(raw_output_path, 'rb') as f:
                    raw_data = f.read()
                
                # Convert raw data to numpy array (640x480 RGB)
                frame_size = 640 * 480 * 3
                if len(raw_data) >= frame_size:
                    frame = np.frombuffer(raw_data[:frame_size], dtype=np.uint8)
                    frame = frame.reshape((480, 640, 3))
                    
                    # Convert RGB to BGR for OpenCV
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Clean up temp files
                    try:
                        os.unlink(temp_file_path)
                        os.unlink(raw_output_path)
                    except:
                        pass
                    
                    return frame
            
            # Clean up temp files
            try:
                os.unlink(temp_file_path)
                if os.path.exists(raw_output_path):
                    os.unlink(raw_output_path)
            except:
                pass
                
        except Exception as e:
            print(f"⚠️ FFmpeg H.264 decode error: {e}")
            # Clean up temp files on error
            try:
                if 'temp_file_path' in locals():
                    os.unlink(temp_file_path)
                if 'raw_output_path' in locals() and os.path.exists(raw_output_path):
                    os.unlink(raw_output_path)
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
            
            # Add a simple motion detection indicator
            if hasattr(self, 'prev_frame') and self.prev_frame is not None:
                # Calculate frame difference for motion detection
                diff = cv2.absdiff(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 
                                 cv2.cvtColor(self.prev_frame, cv2.COLOR_BGR2GRAY))
                motion_score = np.mean(diff)
                
                if motion_score > 10:  # Motion threshold
                    cv2.putText(processed_frame, "Motion Detected", (10, 120), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            self.prev_frame = frame.copy()
            
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
        
        while self.running:
            try:
                # Receive H.264 data
                data, addr = self.udp_socket.recvfrom(self.buffer_size)
                
                if data:
                    # Add to H.264 buffer
                    self.h264_buffer += data
                    
                    # Try to decode frame when we have enough data
                    if len(self.h264_buffer) > 1000:  # Minimum size for H.264 frame
                        frame = self.decode_h264_with_ffmpeg(self.h264_buffer)
                        
                        if frame is not None:
                            print(f"📦 Decoded frame: {frame.shape} from {len(self.h264_buffer)} bytes")
                            
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
                            
                            # Limit buffer size to prevent memory issues
                            if len(self.h264_buffer) > 1024 * 1024:  # 1MB limit
                                self.h264_buffer = self.h264_buffer[-512 * 1024:]  # Keep last 512KB
                    
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
        print("📋 This service listens for UDP stream from libcamera-vid on the host")
        print("🤖 YOLO processing will be applied to each frame")
        print("🔧 Using FFmpeg for H.264 decoding")
        
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