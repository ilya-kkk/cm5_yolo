# Use Ubuntu as base image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV HAILO_ARCH=hailo8l
ENV WORKSPACE=/workspace
ENV DISPLAY=:0

# Create workspace directory
WORKDIR ${WORKSPACE}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-opencv \
    python3-pip \
    python3-dev \
    libcamera-tools \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-x \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 \
    gstreamer1.0-pulseaudio \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    libgstreamer-plugins-good1.0-dev \
    libcamera-dev \
    v4l-utils \
    curl \
    wget \
    ffmpeg \
    netcat \
    && rm -rf /var/lib/apt/lists/*

# Install Hailo Platform
RUN wget -O - https://hailo-hailort.s3.eu-west-2.amazonaws.com/ModelZoo/Releases/Hailo8/v4.0.0/hailo_platform_4.0.0_amd64.deb | dpkg -i - || true \
    && apt-get install -f -y

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    opencv-python \
    numpy \
    Pillow

# Create runtime directory
RUN mkdir -p /tmp/runtime-docker

# Add user to video group for camera access
RUN usermod -a -G video root || true

# Copy project files
COPY . /workspace/

# Set permissions
RUN chmod +x /workspace/*.py /workspace/*.sh

# Default command
CMD ["python3", "/workspace/main_camera_yolo.py"] 