#!/usr/bin/env python3
"""
Test script for libcamera-vid streaming
"""

import subprocess
import time
import signal
import sys

def signal_handler(sig, frame):
    """Handle Ctrl+C signal"""
    print("\nStopping...")
    if hasattr(signal_handler, 'process') and signal_handler.process:
        signal_handler.process.terminate()
        signal_handler.process.wait(timeout=5)
        print("libcamera-vid stopped")
    sys.exit(0)

def main():
    """Main function"""
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Testing libcamera-vid streaming...")
    
    # Check if libcamera-vid is available
    result = subprocess.run(['which', 'libcamera-vid'], capture_output=True, text=True)
    if result.returncode != 0:
        print("libcamera-vid not found")
        return
    
    print("libcamera-vid found, starting stream...")
    
    # Start libcamera-vid streaming process
    stream_cmd = [
        'libcamera-vid',
        '-t', '0',  # Stream indefinitely
        '--codec', 'h264',
        '--width', '640',
        '--height', '480',
        '--framerate', '30',
        '--inline',
        '-o', 'udp://127.0.0.1:5000'  # Stream to local UDP port
    ]
    
    print(f"Command: {' '.join(stream_cmd)}")
    
    try:
        # Start the streaming process
        process = subprocess.Popen(
            stream_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Store reference for signal handler
        signal_handler.process = process
        
        # Wait a bit for the process to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("libcamera-vid streaming started successfully!")
            print("Streaming to udp://127.0.0.1:5000")
            print("Press Ctrl+C to stop")
            
            # Keep running
            while True:
                time.sleep(1)
                if process.poll() is not None:
                    print("libcamera-vid process stopped unexpectedly")
                    break
        else:
            print("libcamera-vid failed to start")
            stdout, stderr = process.communicate()
            print(f"stdout: {stdout.decode()}")
            print(f"stderr: {stderr.decode()}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'process' in locals():
            process.terminate()
            process.wait(timeout=5)

if __name__ == "__main__":
    main() 