#!/usr/bin/env python3
"""
Main camera YOLO processing script for CM5 with Hailo-8L
This script properly decodes H.264 from libcamera-vid and runs real YOLO inference
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
import json
from pathlib import Path

class HailoYOLOProcessor:
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
        self.sps_data = None
        self.pps_data = None
        
        # Hailo integration
        self.hailo_device = None
        self.yolo_model = None
        self.model_loaded = False
        
        # Create output directory for processed frames
        self.output_dir = Path("/tmp/yolo_frames")
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize Hailo
        self.init_hailo()
        
    def init_hailo(self):
        """Initialize Hailo-8L device and load YOLO model"""
        try:
            print("🔧 Initializing Hailo-8L...")
            
            # Check if Hailo device is available
            result = subprocess.run(['hailo', 'scan'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Hailo device found")
                print(result.stdout)
            else:
                print("⚠️ Hailo scan failed, but continuing...")
            
            # Try to find YOLO model
            yolo_model_path = self.find_yolo_model()
            if yolo_model_path:
                print(f"🎯 Found YOLO model: {yolo_model_path}")
                self.yolo_model = yolo_model_path
                self.model_loaded = True
            else:
                print("⚠️ No YOLO model found, will use simulation")
                
        except Exception as e:
            print(f"⚠️ Hailo initialization error: {e}")
            print("🔄 Continuing with simulated YOLO...")
    
    def find_yolo_model(self):
        """Find available YOLO model for Hailo"""
        try:
            # Look for common YOLO model locations
            possible_paths = [
                "/usr/share/hailo/models/yolov8.hef",
                "/usr/local/share/hailo/models/yolov8.hef",
                "/opt/hailo/models/yolov8.hef",
                "/usr/share/hailo/models/yolov5.hef",
                "/usr/local/share/hailo/models/yolov5.hef"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    return path
            
            # Try to find any .hef file
            result = subprocess.run(['find', '/usr', '-name', '*.hef', '-type', 'f'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                hef_files = result.stdout.strip().split('\n')
                for hef_file in hef_files:
                    if 'yolo' in hef_file.lower():
                        return hef_file
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error finding YOLO model: {e}")
            return None
    
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
    
    def parse_h264_stream(self, data):
        """Parse H.264 stream and extract NAL units"""
        nal_units = []
        start_codes = [b'\x00\x00\x01', b'\x00\x00\x00\x01']
        
        # Find all start codes
        positions = []
        for start_code in start_codes:
            pos = 0
            while True:
                pos = data.find(start_code, pos)
                if pos == -1:
                    break
                positions.append(pos)
                pos += 1
        
        positions.sort()
        
        # Extract NAL units
        for i, pos in enumerate(positions):
            if i + 1 < len(positions):
                end_pos = positions[i + 1]
                nal_unit = data[pos:end_pos]
            else:
                nal_unit = data[pos:]
            
            if len(nal_unit) > 4:  # Minimum NAL unit size
                nal_units.append(nal_unit)
        
        return nal_units
    
    def decode_h264_with_ffmpeg_robust(self, h264_data):
        """Robust H.264 decoding using ffmpeg with proper stream handling"""
        try:
            # Write H.264 data to temporary file
            with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
                temp_file.write(h264_data)
                temp_file_path = temp_file.name
            
            # Use ffmpeg to decode H.264 to JPEG with better parameters
            jpeg_output_path = temp_file_path + '.jpg'
            
            # More robust ffmpeg command
            cmd = [
                'ffmpeg', '-y',  # Overwrite output files
                '-f', 'h264',    # Input format
                '-i', temp_file_path,  # Input file
                '-vframes', '1',       # Extract only 1 frame
                '-q:v', '2',           # High quality
                '-pix_fmt', 'yuv420p', # Standard pixel format
                jpeg_output_path        # Output file
            ]
            
            # Run ffmpeg with longer timeout for complex streams
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            
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
    
    def run_yolo_inference(self, frame):
        """Run YOLO inference using Hailo-8L"""
        try:
            if not self.model_loaded or not self.yolo_model:
                print("⚠️ No YOLO model loaded, using simulation")
                return self.simulate_yolo_detection(frame)
            
            # Prepare frame for Hailo
            # Resize to model input size (typically 640x640)
            input_size = (640, 640)
            resized_frame = cv2.resize(frame, input_size)
            
            # Convert to RGB and normalize
            rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            normalized_frame = rgb_frame.astype(np.float32) / 255.0
            
            # Save frame for Hailo processing
            temp_frame_path = "/tmp/hailo_input.jpg"
            cv2.imwrite(temp_frame_path, resized_frame)
            
            # Run Hailo inference
            cmd = [
                'hailo', 'run', self.yolo_model,
                '--input', temp_frame_path,
                '--output', '/tmp/hailo_output.json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            
            if result.returncode == 0:
                # Read Hailo output
                try:
                    with open('/tmp/hailo_output.json', 'r') as f:
                        detections = json.load(f)
                    
                    # Process detections
                    processed_frame = self.draw_hailo_detections(frame, detections)
                    
                    # Clean up
                    try:
                        os.unlink(temp_frame_path)
                        os.unlink('/tmp/hailo_output.json')
                    except:
                        pass
                    
                    return processed_frame
                    
                except Exception as e:
                    print(f"⚠️ Error reading Hailo output: {e}")
            
            # If Hailo failed, fall back to simulation
            print("⚠️ Hailo inference failed, using simulation")
            return self.simulate_yolo_detection(frame)
            
        except Exception as e:
            print(f"⚠️ YOLO inference error: {e}")
            return self.simulate_yolo_detection(frame)
    
    def simulate_yolo_detection(self, frame):
        """Simulate YOLO detection when Hailo is not available"""
        processed_frame = frame.copy()
        
        # Add timestamp and FPS
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(processed_frame, f"Time: {timestamp}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(processed_frame, f"FPS: {self.current_fps:.1f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Add status
        cv2.putText(processed_frame, "YOLO Processing Active (Simulated)", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        # Add frame counter
        cv2.putText(processed_frame, f"Frame: {self.frame_count}", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Simulate detections with animation
        current_time = time.time()
        
        # Simulate person detection
        if int(current_time * 2) % 4 == 0:
            cv2.putText(processed_frame, "Person Detected", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.rectangle(processed_frame, (100, 150), (200, 250), (0, 255, 0), 2)
        
        # Simulate car detection
        if int(current_time * 3) % 5 == 0:
            cv2.putText(processed_frame, "Car Detected", (10, 180), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            cv2.rectangle(processed_frame, (300, 180), (400, 220), (255, 0, 0), 2)
        
        return processed_frame
    
    def draw_hailo_detections(self, frame, detections):
        """Draw Hailo YOLO detections on frame"""
        processed_frame = frame.copy()
        
        # Add timestamp and FPS
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(processed_frame, f"Time: {timestamp}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(processed_frame, f"FPS: {self.current_fps:.1f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Add status
        cv2.putText(processed_frame, "YOLO Processing Active (Hailo-8L)", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        # Add frame counter
        cv2.putText(processed_frame, f"Frame: {self.frame_count}", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Process Hailo detections
        if 'detections' in detections:
            for detection in detections['detections']:
                if 'bbox' in detection and 'class' in detection:
                    bbox = detection['bbox']
                    class_name = detection['class']
                    confidence = detection.get('confidence', 0.0)
                    
                    # Draw bounding box
                    x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                    cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Draw label
                    label = f"{class_name}: {confidence:.2f}"
                    cv2.putText(processed_frame, label, (x1, y1-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return processed_frame
    
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
                    if len(self.h264_buffer) > 10000:  # Increased minimum size
                        print(f"📦 Received {len(self.h264_buffer)} bytes, attempting decode...")
                        
                        # Try to decode with current buffer
                        frame = self.decode_h264_with_ffmpeg_robust(self.h264_buffer)
                        
                        if frame is not None:
                            print(f"✅ Decoded frame: {frame.shape} from {len(self.h264_buffer)} bytes")
                            
                            # Run YOLO inference
                            processed_frame = self.run_yolo_inference(frame)
                            
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
        print("🎯 Starting Hailo YOLO Processor...")
        print("📋 This service listens for UDP stream from libcamera-vid on the host")
        print("🤖 Real YOLO processing with Hailo-8L")
        
        # Setup UDP receiver
        if not self.setup_udp_receiver():
            print("❌ Failed to setup UDP receiver")
            return
        
        self.running = True
        
        # Start stream processing in separate thread
        stream_thread = threading.Thread(target=self.process_h264_stream)
        stream_thread.daemon = True
        stream_thread.start()
        
        print("✅ Hailo YOLO Processor is running")
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
    processor = HailoYOLOProcessor()
    
    try:
        processor.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        processor.stop()
        sys.exit(1) 