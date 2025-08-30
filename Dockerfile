# Use Ubuntu 22.04 with Python 3.10 for better GLIBC compatibility with Hailo
FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace
ENV OPENCV_IO_MAX_IMAGE_PIXELS=2147483647
ENV OPENCV_IO_ENABLE_JASPER=1
ENV HAILO_PLATFORM_PATH=/usr/lib/python3/dist-packages
ENV LD_LIBRARY_PATH=/usr/lib:/usr/local/lib:/usr/lib/python3.10

# Install Python 3.10 and system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    python3.10-venv \
    python3.10-distutils \
    python3.10-minimal \
    python3.10-stdlib \
    python3.10-lib2to3 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libopenblas-dev \
    gfortran \
    wget \
    curl \
    git \
    pciutils \
    udev \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python3
RUN ln -sf /usr/bin/python3.10 /usr/bin/python3
RUN ln -sf /usr/bin/python3.10 /usr/bin/python

# Set working directory
WORKDIR /workspace

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Make Python files executable
RUN chmod +x *.py

# Create symlinks for Hailo packages if they exist on host
RUN mkdir -p /usr/lib/python3/dist-packages /usr/local/lib/python3/dist-packages

# Expose ports
EXPOSE 8080

# Default command - will be overridden by docker-compose
CMD ["python3", "hailo_yolo_main.py"] 