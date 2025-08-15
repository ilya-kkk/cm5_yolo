#!/usr/bin/env python3
"""
SSH-based viewer for YOLO processed video when VPN blocks local network
"""

import paramiko
import time
import os
import glob
from PIL import Image
import io

def ssh_viewer():
    """View processed video frames via SSH"""
    print("SSH-based YOLO Video Viewer")
    print("=" * 40)
    
    # SSH connection details
    hostname = "192.168.0.164"
    username = "cm5"
    password = None  # Will use SSH key
    
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"Connecting to {hostname}...")
        ssh.connect(hostname, username=username)
        print("✅ Connected to CM5")
        
        # Check if frames are being created
        print("\nChecking YOLO processing status...")
        stdin, stdout, stderr = ssh.exec_command("ls -la /tmp/processed_frame_*.jpg 2>/dev/null | wc -l")
        frame_count = stdout.read().decode().strip()
        
        if frame_count == "0":
            print("❌ No processed frames found. YOLO processing might not be running.")
            return
        
        print(f"✅ Found {frame_count} processed frames")
        
        # Get latest frame info
        stdin, stdout, stderr = ssh.exec_command("ls -t /tmp/processed_frame_*.jpg | head -1")
        latest_frame = stdout.read().decode().strip()
        
        if latest_frame:
            print(f"📹 Latest frame: {latest_frame}")
            
            # Download and display the latest frame
            print("\nDownloading latest frame...")
            sftp = ssh.open_sftp()
            
            try:
                # Download the frame
                local_path = "/tmp/latest_frame.jpg"
                sftp.get(latest_frame, local_path)
                
                # Display the image
                print(f"🖼️  Frame downloaded to: {local_path}")
                print("📱 Open this file on your device to view the processed frame")
                
                # Try to open with default image viewer
                try:
                    import subprocess
                    subprocess.run(["xdg-open", local_path], check=True)
                    print("✅ Image opened in default viewer")
                except:
                    print("💡 Manually open the file: /tmp/latest_frame.jpg")
                
            except Exception as e:
                print(f"❌ Error downloading frame: {e}")
            finally:
                sftp.close()
        
        # Show real-time frame count
        print("\n🔄 Monitoring frame creation (press Ctrl+C to stop)...")
        try:
            while True:
                stdin, stdout, stderr = ssh.exec_command("ls -la /tmp/processed_frame_*.jpg 2>/dev/null | wc -l")
                current_count = stdout.read().decode().strip()
                print(f"\r📊 Current frames: {current_count}", end="", flush=True)
                time.sleep(2)
        except KeyboardInterrupt:
            print("\n\n⏹️  Monitoring stopped")
        
    except Exception as e:
        print(f"❌ SSH connection failed: {e}")
        print("\n💡 Make sure:")
        print("   - CM5 is accessible via SSH")
        print("   - SSH key is configured")
        print("   - CM5 IP address is correct")
    
    finally:
        try:
            ssh.close()
            print("🔌 SSH connection closed")
        except:
            pass

if __name__ == "__main__":
    ssh_viewer() 