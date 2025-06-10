# Multi-stage build for better reliability
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    libssl-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN pip install --upgrade pip setuptools wheel

# Copy and install minimal requirements first
COPY backend/requirements-minimal.txt ./requirements-minimal.txt
RUN pip install --no-cache-dir -r requirements-minimal.txt

# Copy and install remaining requirements
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --verbose -r requirements.txt || \
    (echo "Full requirements failed, trying without problematic packages..." && \
     pip install --no-cache-dir google-generativeai supabase || \
     echo "Some packages failed but continuing...")

# Production stage
FROM python:3.11-slim as production

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ .

# TEMPORARILY RUN AS ROOT FOR DEBUGGING
# RUN chown -R appuser:appuser /app
# USER appuser

# Expose port 8080 (Railway's default)
EXPOSE 8080

# Run the application on port 8080 (Railway's expected port)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"] 