# Use Python 3.10 base image for better compatibility
FROM python:3.10-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace
ENV OPENCV_IO_MAX_IMAGE_PIXELS=2147483647
ENV OPENCV_IO_ENABLE_JASPER=1
ENV HAILO_PLATFORM_PATH=/usr/lib/python3/dist-packages
ENV LD_LIBRARY_PATH=/usr/lib:/usr/local/lib

# Install system dependencies
RUN apt-get update && apt-get install -y \
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

# Set working directory
WORKDIR /workspace

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Make Python files executable
RUN chmod +x *.py

# Create symlinks for Hailo packages if they exist on host
RUN mkdir -p /usr/lib/python3/dist-packages /usr/local/lib/python3/dist-packages

# Expose ports
EXPOSE 8080

# Default command - will be overridden by docker-compose
CMD ["python", "hailo_yolo_main.py"] 