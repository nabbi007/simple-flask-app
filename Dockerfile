# Use official Python 3.12 slim image as base
# 'slim' variant is smaller (~120MB vs ~900MB for full image) - excludes unnecessary packages
FROM python:3.12-slim

# Environment Variables:
# PYTHONDONTWRITEBYTECODE=1 - Prevents Python from writing .pyc files to disk (reduces container size)
# PYTHONUNBUFFERED=1 - Forces Python output to be sent straight to terminal without buffering (better for Docker logs)
# PLANNER_DB_PATH - Specifies where SQLite database will be stored (in the persistent volume)
# SECRET_KEY - Flask session secret (CHANGE THIS in production!)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLANNER_DB_PATH=/data/planner.db \
    SECRET_KEY=your-secret-key-change-in-production

# Set working directory inside container where all app files will be copied
WORKDIR /app

# Copy requirements file first (separate layer for better caching)
# Docker caches layers - if requirements.txt hasn't changed, this layer is reused
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir reduces image size by not storing pip's download cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and assets into container
# Separate COPY commands for clarity and potential layer optimization
COPY app.py ./
COPY templates ./templates
COPY static ./static

# Create directory for persistent data (SQLite database)
# This directory will be mounted as a volume to persist data across container restarts
RUN mkdir -p /data

# Define volume mount point for data persistence
# Without this, data would be lost when container is removed
# Usage: docker run -v planner_data:/data ...
VOLUME ["/data"]

# Expose port 5000 (Flask's default port) to the host machine
# This is informational - actual port mapping happens with docker run -p 5000:5000
EXPOSE 5000

# Command to run when container starts
# Executes 'python app.py' to start the Flask development server
CMD ["python", "app.py"]
