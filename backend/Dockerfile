FROM python:3.10-slim

# Install system dependencies in a single line to avoid formatting errors
RUN apt-get update && apt-get install -y build-essential libgl1 libglib2.0-0 libgeos-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway uses the PORT environment variable
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}