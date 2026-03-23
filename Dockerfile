# Use lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ingestionv1.py .

# Set entrypoint (main command)
ENTRYPOINT ["python", "ingestionv1.py"]