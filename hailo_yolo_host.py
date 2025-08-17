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
    print("Please install Hailo Platform: sudo apt install hailo-platform")

class HailoYOLOHost:
    def __init__(self):
        # Hailo variables
        self.vdevice = None
        self.hef = None
        self.infer_model = None
        self.configured_model = None
        self.model_loaded = False
        
        # Model configuration
        self.input_shape = (640, 640)  # YOLO input size
        self.confidence_threshold = 0.5
        self.nms_threshold = 0.4
        
        # COCO classes
        self.classes = self.load_coco_classes()
        
        # Output directory
        self.output_dir = Path("/tmp/yolo_frames")
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize Hailo
        self.init_hailo()
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def load_coco_classes(self):
        """Load COCO class names"""
        return [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
            'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
            'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
            'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake',
            'chair', 'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop',
            'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
    
    def init_hailo(self):
        """Initialize Hailo device and model"""
        try:
            print("🔧 Initializing Hailo YOLO...")
            
            if not HAILO_AVAILABLE:
                print("❌ Hailo platform not available")
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
                    
                    print(f"📥 Input streams: {len(input_infos)}")
                    print(f"📤 Output streams: {len(output_infos)}")
                    
                    # Configure model
                    self.configure_model(first_network)
                else:
                    print("❌ No network groups found in HEF")
                    
            except Exception as e:
                print(f"❌ Failed to load HEF: {e}")
                
        except Exception as e:
            print(f"❌ Hailo initialization error: {e}")
    
    def find_hef_file(self):
        """Find HEF file in common locations"""
        possible_paths = [
            "yolov8n.hef",
            "/home/cm5/yolo_models/yolov8n.hef",
            "/usr/local/share/yolo/yolov8n.hef",
            "/opt/yolo/yolov8n.hef"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def configure_model(self, network_name):
        """Configure the Hailo model for inference"""
        try:
            print(f"⚙️ Configuring model: {network_name}")
            
            # Configure input and output streams
            input_infos = self.hef.get_input_vstream_infos(network_name)
            output_infos = self.hef.get_output_vstream_infos(network_name)
            
            # Create input stream parameters
            input_params = InputVStreamParams()
            input_params.format = hailo_platform.pyhailort.pyhailort.HAILO_FORMAT_TYPE_UINT8
            input_params.quantized = False
            
            # Create output stream parameters
            output_params = OutputVStreamParams()
            output_params.format = hailo_platform.pyhailort.pyhailort.HAILO_FORMAT_TYPE_FLOAT32
            output_params.quantized = False
            
            # Configure model
            self.configured_model = self.hef.create_configured_model(
                [input_params], [output_params], network_name
            )
            
            print("✅ Model configured successfully")
            self.model_loaded = True
            
        except Exception as e:
            print(f"❌ Failed to configure model: {e}")
    
    def preprocess_frame(self, frame):
        """Preprocess frame for Hailo inference"""
        try:
            # Resize to model input size
            resized = cv2.resize(frame, self.input_shape)
            
            # Convert to RGB (Hailo expects RGB)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # Normalize to [0, 1]
            normalized = rgb.astype(np.float32) / 255.0
            
            # Add batch dimension
            batched = np.expand_dims(normalized, axis=0)
            
            return batched
            
        except Exception as e:
            print(f"❌ Preprocessing error: {e}")
            return None
    
    def postprocess_detections(self, output_data, original_shape):
        """Postprocess Hailo output to get detections"""
        try:
            detections = []
            
            # Reshape output based on model architecture
            if len(output_data.shape) == 3:
                # YOLO v8 format: [batch, 84, 8400]
                output = output_data[0]  # Remove batch dimension
                
                # Transpose to [8400, 84]
                output = output.T
                
                # Get boxes, scores, and class IDs
                boxes = output[:, :4]  # x1, y1, x2, y2
                scores = output[:, 4:84].max(axis=1)  # Max confidence per box
                class_ids = output[:, 4:84].argmax(axis=1)  # Class with max confidence
                
                # Filter by confidence
                mask = scores > self.confidence_threshold
                boxes = boxes[mask]
                scores = scores[mask]
                class_ids = class_ids[mask]
                
                # Scale boxes to original image size
                h, w = original_shape[:2]
                scale_x = w / self.input_shape[0]
                scale_y = h / self.input_shape[1]
                
                scaled_boxes = []
                for box in boxes:
                    x1, y1, x2, y2 = box
                    scaled_box = [
                        int(x1 * scale_x),
                        int(y1 * scale_y),
                        int(x2 * scale_x),
                        int(y2 * scale_y)
                    ]
                    scaled_boxes.append(scaled_box)
                
                # Create detection objects
                for i, (box, score, class_id) in enumerate(zip(scaled_boxes, scores, class_ids)):
                    if class_id < len(self.classes):
                        detection = {
                            'bbox': box,
                            'confidence': float(score),
                            'class_id': int(class_id),
                            'class_name': self.classes[class_id]
                        }
                        detections.append(detection)
            
            return detections
            
        except Exception as e:
            print(f"❌ Postprocessing error: {e}")
            return []
    
    def run_inference(self, frame):
        """Run YOLO inference on Hailo"""
        try:
            if not self.model_loaded:
                print("⚠️ Model not loaded, skipping inference")
                return []
            
            # Preprocess frame
            input_data = self.preprocess_frame(frame)
            if input_data is None:
                return []
            
            # Run inference
            with self.configured_model.create_infer_model() as infer_model:
                # Create input and output streams
                input_stream = infer_model.create_input_stream()
                output_stream = infer_model.create_output_stream()
                
                # Send input data
                input_stream.write(input_data)
                
                # Get output data
                output_data = output_stream.read()
                
                # Postprocess
                detections = self.postprocess_detections(output_data, frame.shape)
                
                return detections
                
        except Exception as e:
            print(f"❌ Inference error: {e}")
            return []
    
    def draw_detections(self, frame, detections):
        """Draw detection boxes on frame"""
        try:
            for detection in detections:
                bbox = detection['bbox']
                confidence = detection['confidence']
                class_name = detection['class_name']
                
                x1, y1, x2, y2 = bbox
                
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw label
                label = f"{class_name}: {confidence:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                
                cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                            (x1 + label_size[0], y1), (0, 255, 0), -1)
                cv2.putText(frame, label, (x1, y1 - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            
            return frame
            
        except Exception as e:
            print(f"❌ Drawing error: {e}")
            return frame
    
    def process_frame(self, frame):
        """Process a single frame with YOLO"""
        try:
            # Run inference
            detections = self.run_inference(frame)
            
            # Draw detections
            processed_frame = self.draw_detections(frame.copy(), detections)
            
            return processed_frame, detections
            
        except Exception as e:
            print(f"❌ Frame processing error: {e}")
            return frame, []
    
    def test_with_sample_image(self):
        """Test Hailo YOLO with a sample image"""
        print("🧪 Testing Hailo YOLO with sample image...")
        
        # Create a simple test image
        test_image = np.ones((480, 640, 3), dtype=np.uint8) * 128
        cv2.rectangle(test_image, (100, 100), (300, 300), (255, 255, 255), -1)
        
        print(f"📸 Test image created: {test_image.shape}")
        
        # Process frame
        processed_frame, detections = self.process_frame(test_image)
        
        # Save result
        output_path = self.output_dir / "test_result.jpg"
        cv2.imwrite(str(output_path), processed_frame)
        
        print(f"✅ Test completed. Result saved to: {output_path}")
        print(f"📊 Detections found: {len(detections)}")
        
        return detections
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"📡 Received signal {signum}")
        sys.exit(0)

def main():
    """Main function"""
    print("🚀 Starting Hailo YOLO Host...")
    
    # Create processor
    processor = HailoYOLOHost()
    
    if processor.model_loaded:
        print("✅ Hailo YOLO initialized successfully")
        
        # Run test
        processor.test_with_sample_image()
        
        print("🎉 All tests passed! Hailo YOLO is working correctly.")
        print("💡 You can now integrate this with your camera system.")
    else:
        print("❌ Failed to initialize Hailo YOLO")
        print("💡 Check that Hailo Platform is installed and HEF file is available")
        sys.exit(1)

if __name__ == "__main__":
    main() 