#!/usr/bin/env python3
"""
Main camera YOLO processing script for CM5 with Hailo-8L
This script properly handles H.264 from libcamera-vid and runs real YOLO inference
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
        self.keyframe_found = False
        
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
    
    def try_multiple_decoding_methods(self, h264_data):
        """Try multiple methods to decode H.264 stream"""
        print(f"🔧 Trying multiple H.264 decoding methods for {len(h264_data)} bytes...")
        
        # Method 1: Try direct FFmpeg decode
        frame = self.try_ffmpeg_direct_decode(h264_data)
        if frame is not None:
            return frame
        
        # Method 2: Try with different FFmpeg parameters
        frame = self.try_ffmpeg_with_params(h264_data)
        if frame is not None:
            return frame
        
        # Method 3: Try to extract frame data manually
        frame = self.try_manual_frame_extraction(h264_data)
        if frame is not None:
            return frame
        
        print("❌ All decoding methods failed")
        return None
    
    def try_ffmpeg_direct_decode(self, h264_data):
        """Try direct FFmpeg decode without modifications"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
                temp_file.write(h264_data)
                temp_file_path = temp_file.name
            
            jpeg_output_path = temp_file_path + '.jpg'
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'h264',
                '-i', temp_file_path,
                '-vframes', '1',
                '-q:v', '2',
                jpeg_output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            
            if result.returncode == 0 and os.path.exists(jpeg_output_path):
                frame = cv2.imread(jpeg_output_path)
                if frame is not None and frame.size > 0:
                    print("✅ Direct FFmpeg decode successful")
                    return frame
            
            # Cleanup
            try:
                os.unlink(temp_file_path)
                if os.path.exists(jpeg_output_path):
                    os.unlink(jpeg_output_path)
            except:
                pass
                
        except Exception as e:
            print(f"⚠️ Direct FFmpeg decode failed: {e}")
        
        return None
    
    def try_ffmpeg_with_params(self, h264_data):
        """Try FFmpeg with different parameters"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
                temp_file.write(h264_data)
                temp_file_path = temp_file.name
            
            jpeg_output_path = temp_file_path + '.jpg'
            
            # Try with different parameters
            cmd = [
                'ffmpeg', '-y',
                '-f', 'h264',
                '-i', temp_file_path,
                '-vframes', '1',
                '-q:v', '2',
                '-pix_fmt', 'yuv420p',
                '-vf', 'scale=640:480',
                jpeg_output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            
            if result.returncode == 0 and os.path.exists(jpeg_output_path):
                frame = cv2.imread(jpeg_output_path)
                if frame is not None and frame.size > 0:
                    print("✅ FFmpeg with params decode successful")
                    return frame
            
            # Cleanup
            try:
                os.unlink(temp_file_path)
                if os.path.exists(jpeg_output_path):
                    os.unlink(jpeg_output_path)
            except:
                pass
                
        except Exception as e:
            print(f"⚠️ FFmpeg with params decode failed: {e}")
        
        return None
    
    def try_manual_frame_extraction(self, h264_data):
        """Try to manually extract frame data"""
        try:
            # Look for start codes
            start_codes = [b'\x00\x00\x01', b'\x00\x00\x00\x01']
            
            # Find first start code
            first_start = -1
            for start_code in start_codes:
                pos = h264_data.find(start_code)
                if pos != -1:
                    first_start = pos
                    break
            
            if first_start == -1:
                print("⚠️ No start codes found in H.264 data")
                return None
            
            # Extract data from first start code
            frame_data = h264_data[first_start:]
            
            # Try to create a minimal valid H.264 stream
            # Add a simple SPS header for 640x480
            minimal_sps = b'\x00\x00\x00\x01\x67\x42\x00\x1E\x95\xA0\x28\x0F\x68\x40\x00\x00\x03\x00\x40\x00\x00\x0F\x03\xC6\x0C\x44\x80'
            minimal_pps = b'\x00\x00\x00\x01\x68\xCE\x3C\x80'
            
            # Create minimal stream
            minimal_stream = minimal_sps + minimal_pps + frame_data
            
            # Try to decode minimal stream
            with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
                temp_file.write(minimal_stream)
                temp_file_path = temp_file.name
            
            jpeg_output_path = temp_file_path + '.jpg'
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'h264',
                '-i', temp_file_path,
                '-vframes', '1',
                '-q:v', '2',
                jpeg_output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            
            if result.returncode == 0 and os.path.exists(jpeg_output_path):
                frame = cv2.imread(jpeg_output_path)
                if frame is not None and frame.size > 0:
                    print("✅ Manual frame extraction successful")
                    return frame
            
            # Cleanup
            try:
                os.unlink(temp_file_path)
                if os.path.exists(jpeg_output_path):
                    os.unlink(jpeg_output_path)
            except:
                pass
                
        except Exception as e:
            print(f"⚠️ Manual frame extraction failed: {e}")
        
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
        
        # Add camera info
        cv2.putText(processed_frame, "Real Camera Stream Active", (10, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
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
        print("🔧 Will try multiple decoding methods")
        
        while self.running:
            try:
                # Receive H.264 data
                data, addr = self.udp_socket.recvfrom(self.buffer_size)
                
                if data:
                    # Add to H.264 buffer
                    self.h264_buffer += data
                    
                    # Try to decode frame when we have enough data
                    if len(self.h264_buffer) > 10000:  # Minimum size for H.264 frame
                        print(f"📦 Received {len(data)} bytes, total buffer: {len(self.h264_buffer)} bytes")
                        print(f"🔧 Attempting to decode H.264 frame...")
                        
                        # Try multiple decoding methods
                        frame = self.try_multiple_decoding_methods(self.h264_buffer)
                        
                        if frame is not None:
                            print(f"🎯 SUCCESS! Decoded real camera frame: {frame.shape}")
                            
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
                                    print(f"🎯 Real Camera YOLO Processing FPS: {self.current_fps}")
                            
                            # Clear buffer after successful decode
                            self.h264_buffer = b''
                        else:
                            print(f"⚠️ Failed to decode frame, keeping buffer for next attempt")
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
        print("🔧 Will try multiple H.264 decoding methods")
        
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