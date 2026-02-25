# Use Python 3.10 slim for ARM64 compatibility
FROM python:3.10-slim

# Install system dependencies for ezdxf, OpenCV (YOLO), and PyMuPDF
RUN apt-get update && apt-get install -y 
    build-essential 
    libgl1-mesa-glx 
    libglib2.0-0 
    libgeos-dev 
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
