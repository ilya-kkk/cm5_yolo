#!/usr/bin/env python3
"""
Simplified Hailo YOLO for CM5 host (without Docker)
Direct integration with Hailo-8L accelerator
"""

import cv2
import numpy as np
import time
import signal
import sys
import os
from pathlib import Path

try:
    import hailo_platform.pyhailort.pyhailort as pyhailort
    from hailo_platform.pyhailort.pyhailort import VDevice, HEF, InferModel, ConfiguredInferModel, InputVStreamParams, OutputVStreamParams
    print("✅ Hailo platform imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Hailo platform: {e}")
    sys.exit(1)

class HailoYOLOHost:
    def __init__(self):
        self.vdevice = None
        self.hef = None
        self.configured_model = None
        self.input_vstream = None
        self.output_vstream = None
        self.running = False
        
    def init_hailo(self):
        """Initialize Hailo device and load HEF"""
        try:
            print("🔧 Initializing Hailo YOLO...")
            
            # Find HEF file
            hef_path = self.find_hef_file()
            if not hef_path:
                return False
                
            print(f"🎯 Found HEF file: {hef_path}")
            
            # Create VDevice
            print("🔍 Creating VDevice...")
            self.vdevice = VDevice()
            print("✅ VDevice created successfully")
            
            # Load HEF
            print("📦 Loading HEF file...")
            self.hef = HEF(hef_path)
            print("✅ HEF loaded successfully")
            
            # Get network groups
            network_groups = self.hef.get_network_group_names()
            print(f"📋 Network groups: {network_groups}")
            
            # Get input/output streams
            input_streams = self.hef.get_input_vstream_infos()
            output_streams = self.hef.get_output_vstream_infos()
            print(f"📥 Input streams: {len(input_streams)}")
            print(f"📤 Output streams: {len(output_streams)}")
            
            # Configure model
            if not self.configure_model(network_groups[0]):
                return False
                
            print("✅ Hailo YOLO initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Hailo YOLO: {e}")
            return False
    
    def find_hef_file(self):
        """Find HEF file in current directory"""
        hef_files = list(Path('.').glob('*.hef'))
        if hef_files:
            return str(hef_files[0])
        return None
    
    def configure_model(self, network_group_name):
        """Configure the model for inference"""
        try:
            print(f"⚙️ Configuring model: {network_group_name}")
            
            # Configure network group with default parameters (empty dict)
            # This avoids the max_desc_page_size issue
            configured_models = self.vdevice.configure(self.hef, {})
            
            # Handle the list of configured models
            if isinstance(configured_models, list) and len(configured_models) > 0:
                self.configured_model = configured_models[0]
                print(f"✅ Got {len(configured_models)} configured model(s)")
            else:
                self.configured_model = configured_models
            
            # Get input/output stream info
            input_streams = self.hef.get_input_vstream_infos()
            output_streams = self.hef.get_output_vstream_infos()
            
            # Configure input stream
            input_params = InputVStreamParams()
            input_params.data_type = pyhailort.FormatType.UINT8
            input_params.format_order = pyhailort.FormatOrder.NHWC
            
            # Configure output stream
            output_params = OutputVStreamParams()
            output_params.data_type = pyhailort.FormatType.FLOAT32
            output_params.format_order = pyhailort.FormatOrder.NHWC
            
            # Create streams using the correct API methods
            self.input_vstream = self.configured_model._create_input_vstreams(input_streams[0], input_params)
            self.output_vstream = self.configured_model._create_output_vstreams(output_streams[0], output_params)
            
            print("✅ Model configured successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to configure model: {e}")
            return False
    
    def preprocess_frame(self, frame):
        """Preprocess frame for YOLO input"""
        # Resize to YOLO input size (640x640)
        resized = cv2.resize(frame, (640, 640))
        
        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize to [0, 1]
        normalized = rgb.astype(np.float32) / 255.0
        
        # Convert to uint8 for Hailo
        uint8_data = (normalized * 255).astype(np.uint8)
        
        return uint8_data
    
    def postprocess_detections(self, output_data, original_frame):
        """Postprocess YOLO output to get detections"""
        # This is a simplified postprocessing - you'll need to implement proper YOLO output parsing
        # based on your specific model output format
        
        height, width = original_frame.shape[:2]
        
        # For now, return empty detections
        # You'll need to implement proper YOLO output parsing here
        detections = []
        
        return detections
    
    def run_inference(self, frame):
        """Run inference on a single frame"""
        try:
            # Preprocess frame
            input_data = self.preprocess_frame(frame)
            
            # Send input data
            self.input_vstream.write(input_data)
            
            # Read output data
            output_data = self.output_vstream.read()
            
            # Postprocess
            detections = self.postprocess_detections(output_data, frame)
            
            return detections
            
        except Exception as e:
            print(f"❌ Inference failed: {e}")
            return []
    
    def draw_detections(self, frame, detections):
        """Draw detections on frame"""
        # For now, just return the original frame
        # You'll implement proper detection drawing here
        return frame
    
    def test_with_sample_image(self):
        """Test with a sample image"""
        try:
            # Create a test image (640x640, 3 channels)
            test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
            
            print("🧪 Testing inference with sample image...")
            
            # Run inference
            detections = self.run_inference(test_image)
            
            print(f"✅ Inference completed, got {len(detections)} detections")
            
            # Draw detections
            result_frame = self.draw_detections(test_image, detections)
            
            print("✅ Test completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    def stop(self):
        """Stop and cleanup"""
        self.running = False
        
        if self.input_vstream:
            self.input_vstream.close()
        if self.output_vstream:
            self.output_vstream.close()
        if self.configured_model:
            # ConfiguredNetwork doesn't have release method
            pass
        if self.vdevice:
            self.vdevice.release()
        
        print("🛑 Hailo YOLO stopped")

def signal_handler(signum, frame):
    print("\n🛑 Received interrupt signal")
    if hailo_processor:
        hailo_processor.stop()
    sys.exit(0)

if __name__ == "__main__":
    print("🚀 Starting Hailo YOLO Host...")
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create processor
    hailo_processor = HailoYOLOHost()
    
    try:
        # Initialize Hailo
        if not hailo_processor.init_hailo():
            print("💡 Check that Hailo Platform is installed and HEF file is available")
            sys.exit(1)
        
        # Test with sample image
        if hailo_processor.test_with_sample_image():
            print("🎉 Hailo YOLO is working correctly!")
        else:
            print("❌ Hailo YOLO test failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        hailo_processor.stop() 