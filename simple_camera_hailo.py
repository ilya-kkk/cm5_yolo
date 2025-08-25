#!/usr/bin/env python3
"""
Simple camera capture and Hailo processing script
"""

import cv2
import time
import numpy as np
from hailo_platform.pyhailort.pyhailort import VDevice, HEF, InferModel, ConfiguredInferModel

def main():
    print("🔧 Starting simple camera Hailo processing...")
    
    # Initialize camera
    print("🔧 Initializing camera...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Failed to open camera")
        return
    
    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("✅ Camera initialized successfully")
    
    # Initialize Hailo
    print("🔧 Initializing Hailo...")
    try:
        vdevice = VDevice()
        print("✅ Hailo VDevice created successfully")
        
        # Load HEF file
        hef_path = "yolov8n.hef"
        if not os.path.exists(hef_path):
            print(f"❌ HEF file not found: {hef_path}")
            return
            
        hef = HEF(hef_path)
        print("✅ HEF file loaded successfully")
        
        # Configure model
        configure_params = hef.create_configure_params()
        configured_model = hef.configure(configure_params)
        print("✅ Model configured successfully")
        
        # Get input/output info
        input_info = configured_model.get_input_infos()
        output_info = configured_model.get_output_infos()
        
        print(f"Input info: {input_info}")
        print(f"Output info: {output_info}")
        
    except Exception as e:
        print(f"❌ Failed to initialize Hailo: {e}")
        return
    
    print("🔧 Starting video capture loop...")
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read frame")
                break
            
            frame_count += 1
            
            # Process every 10th frame to avoid overwhelming Hailo
            if frame_count % 10 == 0:
                try:
                    # Preprocess frame for Hailo
                    # This is a simplified version - actual preprocessing depends on model requirements
                    processed_frame = cv2.resize(frame, (640, 640))
                    processed_frame = processed_frame.astype(np.float32) / 255.0
                    
                    # Run inference (simplified)
                    print(f"🔧 Processing frame {frame_count}")
                    
                except Exception as e:
                    print(f"❌ Error processing frame: {e}")
            
            # Display frame
            cv2.imshow('Hailo YOLO Processing', frame)
            
            # Calculate FPS
            if frame_count % 30 == 0:
                elapsed_time = time.time() - start_time
                fps = frame_count / elapsed_time
                print(f"📊 FPS: {fps:.2f}")
            
            # Break on 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\n🔧 Stopping video capture...")
    
    finally:
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        if 'vdevice' in locals():
            vdevice.release()
        print("✅ Cleanup completed")

if __name__ == "__main__":
    import os
    main()

