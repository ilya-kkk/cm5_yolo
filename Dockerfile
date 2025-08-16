# Use Python 3.10 full image with NumPy pre-installed
FROM python:3.10

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/usr/local/lib/python3.10/site-packages
ENV OPENCV_IO_MAX_IMAGE_PIXELS=2147483647
ENV OPENCV_IO_ENABLE_JASPER=1

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
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x *.py

# Expose ports
EXPOSE 8080

# Default command - will be overridden by docker-compose
CMD ["python3", "hailo_yolo_direct.py"] 