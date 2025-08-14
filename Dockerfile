# Use official Hailo Docker image as base
FROM hailoai/hailo8:latest

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
    python3-opencv \
    python3-pip \
    python3-dev \
    libcamera-tools \
    libcamera-apps \
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
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-good1.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    libgstreamer-plugins-ugly1.0-dev \
    libgstreamer-libav1.0-dev \
    libgstreamer-x1.0-dev \
    libgstreamer-alsa1.0-dev \
    libgstreamer-gl1.0-dev \
    libgstreamer-gtk-3.0-dev \
    libgstreamer-qt5-1.0-dev \
    libgstreamer-pulseaudio1.0-dev \
    libcamera-dev \
    libcamera-apps-dev \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    opencv-python \
    numpy \
    hailo-platform \
    Pillow

# Create runtime directory
RUN mkdir -p /tmp/runtime-docker

# Copy project files
COPY . /workspace/

# Set permissions
RUN chmod +x /workspace/*.py /workspace/*.sh

# Default command
CMD ["python3", "/workspace/main_camera_yolo.py"] 