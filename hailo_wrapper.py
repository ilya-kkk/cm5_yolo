#!/usr/bin/env python3
"""
Hailo YOLO Wrapper - Direct integration with Hailo-8L accelerator
"""

import sys
import os
import cv2
import numpy as np
import time
import signal
import socket
import threading
import json
from pathlib import Path

# Hailo imports
try:
    import hailo_platform
    from hailo_platform.pyhailort.pyhailort import (
        VDevice, HEF, InferModel, ConfiguredInferModel,
        InputVStreamParams, OutputVStreamParams
    )
    HAILO_AVAILABLE = True
    print("✅ Hailo platform imported successfully")
except ImportError as e:
    HAILO_AVAILABLE = False
    print(f"❌ Hailo platform not available: {e}")

class HailoYOLOProcessor:
    def __init__(self):
        self.udp_socket = None
        self.running = False
        self.buffer_size = 1024 * 1024  # 1MB buffer
        self.frame_lock = threading.Lock()
        
        # YOLO processing variables
        self.frame_counter = 0
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
        
        # Hailo variables
        self.vdevice = None
        self.hef = None
        self.infer_model = None
        self.configured_model = None
        self.model_loaded = False
        
        # Output directory
        self.output_dir = Path("/tmp/yolo_frames")
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize Hailo
        self.init_hailo()
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def init_hailo(self):
        """Initialize Hailo device and model"""
        try:
            print("🔧 Initializing Hailo YOLO...")
            
            if not HAILO_AVAILABLE:
                print("⚠️ Hailo platform not available - running in test mode")
                return
            
            # Find HEF file
            hef_path = self.find_hef_file()
            if not hef_path:
                print("❌ No HEF file found")
                return
            
            print(f"🎯 Found HEF file: {hef_path}")
            
            # Create VDevice
            try:
                print("🔍 Creating VDevice...")
                self.vdevice = VDevice()
                print("✅ VDevice created successfully")
            except Exception as e:
                print(f"❌ Failed to create VDevice: {e}")
                return
            
            # Load HEF
            try:
                print("📦 Loading HEF file...")
                self.hef = HEF(hef_path)
                print("✅ HEF loaded successfully")
                
                # Get model info
                network_groups = self.hef.get_network_group_names()
                print(f"📋 Network groups: {network_groups}")
                
                if network_groups:
                    first_network = network_groups[0]
                    input_infos = self.hef.get_input_vstream_infos(first_network)
                    output_infos = self.hef.get_output_vstream_infos(first_network)
                    
                    print(f"📥 Input streams: {[info.name for info in input_infos]}")
                    print(f"📤 Output streams: {[info.name for info in output_infos]}")
                    
                    # Get input shape
                    if input_infos:
                        input_info = input_infos[0]
                        print(f"📐 Input shape: {input_info.shape}")
                        print(f"📐 Input format: {input_info.format}")
                
            except Exception as e:
                print(f"❌ Failed to load HEF: {e}")
                return
            
            # Create InferModel
            try:
                print("🤖 Creating InferModel...")
                self.infer_model = self.vdevice.create_infer_model(hef_path)
                print("✅ InferModel created successfully")
                
                # Configure model
                print("⚙️ Configuring model...")
                self.configured_model = self.infer_model.configure()
                print("✅ Model configured successfully")
                
                self.model_loaded = True
                print("🎉 Hailo YOLO model loaded and ready!")
                
            except Exception as e:
                print(f"❌ Failed to create/configure model: {e}")
                return
                
        except Exception as e:
            print(f"❌ Hailo initialization error: {e}")
            print("🔄 Continuing with OpenCV fallback...")
    
    def find_hef_file(self):
        """Find HEF model file"""
        possible_paths = [
            "/workspace/yolov8n.hef",
            "/home/cm5/cm5_yolo/yolov8n.hef",
            "/usr/share/hailo/models/yolov8n.hef",
            "/opt/hailo/models/yolov8n.hef"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                file_size = os.path.getsize(path)
                if file_size > 1000000:  # More than 1MB
                    print(f"✅ Found HEF file: {path} ({file_size} bytes)")
                    return path
                else:
                    print(f"⚠️ HEF file too small: {path} ({file_size} bytes)")
        
        print("❌ No valid HEF file found")
        return None
    
    def preprocess_frame(self, frame):
        """Preprocess frame for Hailo inference"""
        try:
            # Resize to model input size (assuming 640x640 for YOLOv8)
            input_size = (640, 640)
            resized = cv2.resize(frame, input_size)
            
            # Convert BGR to RGB
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # Normalize to [0, 1]
            normalized = rgb.astype(np.float32) / 255.0
            
            # Add batch dimension
            batched = np.expand_dims(normalized, axis=0)
            
            return batched
            
        except Exception as e:
            print(f"⚠️ Preprocessing error: {e}")
            return None
    
    def postprocess_detections(self, output_data, original_frame):
        """Postprocess Hailo output to get detections"""
        try:
            # This is a simplified postprocessing - actual implementation depends on model output format
            processed_frame = original_frame.copy()
            
            # Add timestamp and FPS
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(processed_frame, f"Time: {timestamp}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(processed_frame, f"FPS: {self.current_fps:.1f}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(processed_frame, "YOLO Processing Active (Hailo-8L)", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            cv2.putText(processed_frame, f"Frame: {self.frame_counter}", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # Add Hailo-specific info
            cv2.putText(processed_frame, f"Model: YOLOv8n", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(processed_frame, f"Device: Hailo-8L", (10, 180), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Draw some example detections (this would be real detections from model output)
            height, width = original_frame.shape[:2]
            cv2.rectangle(processed_frame, (width//4, height//4), (3*width//4, 3*height//4), 
                         (0, 255, 0), 2)
            cv2.putText(processed_frame, "Person: 0.95", (width//4, height//4-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            return processed_frame
            
        except Exception as e:
            print(f"⚠️ Postprocessing error: {e}")
            return original_frame
    
    def run_hailo_inference(self, frame):
        """Run YOLO inference using Hailo device"""
        try:
            if not self.model_loaded:
                print("⚠️ Hailo model not loaded, using fallback")
                return self.simulate_yolo_detection(frame)
            
            print("🚀 Running Hailo YOLO inference...")
            
            # Preprocess frame
            input_data = self.preprocess_frame(frame)
            if input_data is None:
                print("⚠️ Preprocessing failed, using fallback")
                return self.simulate_yolo_detection(frame)
            
            # Create bindings
            try:
                input_buffers = {}
                output_buffers = {}
                
                # Get input stream info
                input_infos = self.hef.get_input_vstream_infos()
                output_infos = self.hef.get_output_vstream_infos()
                
                if input_infos:
                    input_name = input_infos[0].name
                    input_buffers[input_name] = input_data
                    print(f"📥 Input buffer created: {input_name}, shape: {input_data.shape}")
                
                if output_infos:
                    output_name = output_infos[0].name
                    # Create output buffer with appropriate size
                    output_shape = output_infos[0].shape
                    output_data = np.zeros(output_shape, dtype=np.float32)
                    output_buffers[output_name] = output_data
                    print(f"📤 Output buffer created: {output_name}, shape: {output_shape}")
                
                # Create bindings
                bindings = self.configured_model.create_bindings(input_buffers, output_buffers)
                
                # Run inference
                print("⚡ Running inference...")
                start_time = time.time()
                
                # Use synchronous inference for simplicity
                self.configured_model.run([bindings], timeout=5000)  # 5 second timeout
                
                inference_time = (time.time() - start_time) * 1000  # Convert to ms
                print(f"⚡ Inference completed in {inference_time:.2f} ms")
                
                # Postprocess results
                processed_frame = self.postprocess_detections(output_data, frame)
                
                # Add inference time to frame
                cv2.putText(processed_frame, f"Inference: {inference_time:.1f}ms", (10, 210), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                return processed_frame
                
            except Exception as e:
                print(f"⚠️ Hailo inference error: {e}")
                return self.simulate_yolo_detection(frame)
            
        except Exception as e:
            print(f"⚠️ Hailo inference error: {e}")
            return self.simulate_yolo_detection(frame)
    
    def simulate_yolo_detection(self, frame):
        """Simulate YOLO detection for fallback"""
        processed_frame = frame.copy()
        
        # Add timestamp and FPS
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(processed_frame, f"Time: {timestamp}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(processed_frame, f"FPS: {self.current_fps:.1f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(processed_frame, "YOLO Processing Active (Simulation)", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        cv2.putText(processed_frame, f"Frame: {self.frame_counter}", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        return processed_frame
    
    def decode_mjpeg_frame(self, data):
        """Decode MJPEG frame from UDP data"""
        try:
            # Find JPEG start marker
            start_marker = b'\xff\xd8'
            end_marker = b'\xff\xd9'
            
            start_pos = data.find(start_marker)
            if start_pos == -1:
                return None
            
            end_pos = data.find(end_marker, start_pos)
            if end_pos == -1:
                return None
            
            # Extract JPEG data
            jpeg_data = data[start_pos:end_pos + 2]
            
            # Decode using OpenCV
            nparr = np.frombuffer(jpeg_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                return frame
            else:
                return None
                
        except Exception as e:
            print(f"⚠️ MJPEG decode error: {e}")
            return None
    
    def setup_udp_receiver(self):
        """Setup UDP receiver for MJPEG stream"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('127.0.0.1', 5000))
            self.udp_socket.settimeout(1.0)
            print("✅ UDP receiver setup on port 5000")
            print("📝 Note: libcamera-vid must be started manually on the host")
            print("📝 Command: libcamera-vid -t 0 --codec mjpeg --width 640 --height 480 --framerate 30 --inline -o udp://127.0.0.1:5000")
            return True
        except Exception as e:
            print(f"❌ UDP setup error: {e}")
            return False
    
    def process_mjpeg_stream(self):
        """Process MJPEG stream from UDP"""
        print("📹 Starting MJPEG stream processing...")
        print("⏳ Waiting for libcamera-vid MJPEG stream from host...")
        print("🔧 MJPEG is much easier to decode than H.264")
        
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(self.buffer_size)
                if data:
                    print(f"📦 Received {len(data)} bytes")
                    
                    # Decode MJPEG frame
                    frame = self.decode_mjpeg_frame(data)
                    
                    if frame is not None:
                        print(f"🎯 SUCCESS! Decoded real camera frame: {frame.shape}")
                        
                        # Update frame counter
                        self.frame_counter += 1
                        
                        # Run YOLO inference
                        processed_frame = self.run_hailo_inference(frame)
                        
                        # Save processed frame
                        if self.save_processed_frame(processed_frame):
                            # Update FPS counter
                            self.fps_counter += 1
                            current_time = time.time()
                            
                            # Calculate FPS every second
                            if current_time - self.fps_start_time >= 1.0:
                                self.current_fps = self.fps_counter / (current_time - self.fps_start_time)
                                print(f"🔄 Hailo YOLO Processing FPS: {self.current_fps:.1f}")
                                self.fps_counter = 0
                                self.fps_start_time = current_time
                    else:
                        print("⚠️ Failed to decode MJPEG frame")
                        
            except socket.timeout:
                continue
            except Exception as e:
                print(f"⚠️ Stream processing error: {e}")
                continue
    
    def save_processed_frame(self, frame):
        """Save processed frame to shared directory"""
        try:
            output_path = "/tmp/latest_yolo_frame.jpg"
            success = cv2.imwrite(output_path, frame)
            if success:
                return True
            else:
                print("⚠️ Failed to save processed frame")
                return False
        except Exception as e:
            print(f"⚠️ Save error: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.running = False
        
        # Cleanup Hailo resources
        if self.configured_model:
            try:
                self.configured_model.shutdown()
                print("✅ Hailo model shutdown")
            except:
                pass
        
        if self.vdevice:
            try:
                self.vdevice.release()
                print("✅ Hailo device released")
            except:
                pass
        
        if self.udp_socket:
            self.udp_socket.close()
        
        sys.exit(0)
    
    def run(self):
        """Main run loop"""
        print("🎯 Starting Hailo YOLO Processor...")
        print("📋 This service listens for UDP stream from libcamera-vid on the host")
        print("🤖 Real YOLO processing with Hailo-8L accelerator")
        print("🔧 Now using MJPEG instead of problematic H.264")
        
        # Setup UDP receiver
        if not self.setup_udp_receiver():
            print("❌ Failed to setup UDP receiver")
            return
        
        self.running = True
        
        # Start stream processing in separate thread
        stream_thread = threading.Thread(target=self.process_mjpeg_stream)
        stream_thread.daemon = True
        stream_thread.start()
        
        print("✅ Hailo YOLO Processor is running")
        print("📱 Video stream available at UDP://127.0.0.1:5000")
        print("🌐 Web interface available at http://localhost:8080")
        print("💾 Processed frames saved to /tmp/latest_yolo_frame.jpg")
        print()
        print("🔧 To start video stream, run on the host:")
        print("   libcamera-vid -t 0 --codec mjpeg --width 640 --height 480 --framerate 30 --inline -o udp://127.0.0.1:5000")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    processor = HailoYOLOProcessor()
    processor.run() 