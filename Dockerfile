# Use Ubuntu 20.04 with Python 3.8 for maximum GLIBC compatibility with CM5
FROM ubuntu:20.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/usr/local/lib/python3.8/site-packages:/usr/lib/python3/dist-packages:/usr/lib/python3.8/dist-packages
ENV OPENCV_IO_MAX_IMAGE_PIXELS=2147483647
ENV OPENCV_IO_ENABLE_JASPER=1
ENV HAILO_PLATFORM_PATH=/usr/lib/python3/dist-packages
ENV LD_LIBRARY_PATH=/usr/lib:/usr/local/lib

# Install Python 3.8 and system dependencies
RUN apt-get update && apt-get install -y \
    python3.8 \
    python3.8-dev \
    python3-pip \
    python3.8-venv \
    python3.8-distutils \
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
RUN ln -sf /usr/bin/python3.8 /usr/bin/python3
RUN ln -sf /usr/bin/python3.8 /usr/bin/python

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