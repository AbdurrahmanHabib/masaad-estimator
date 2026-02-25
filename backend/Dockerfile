# Stage 1: Build stage
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y build-essential libgeos-dev

# Install CPU-only PyTorch first to save massive space (4GB+)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install remaining requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final Runtime stage
FROM python:3.10-slim

WORKDIR /app

# Install only necessary runtime libraries
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Set environment variable to force CPU mode for AI
ENV ONNXRUNTIME_EXECUTION_MODE=CPU
ENV PORT=8000

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT