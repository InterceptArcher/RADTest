# Dockerfile for ephemeral Railway worker
# This container handles intelligence gathering, validation, and slideshow generation

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY *.py ./

# Create output directory for results
RUN mkdir -p /output

# Set environment for Railway
ENV PYTHONUNBUFFERED=1

# Run the worker
CMD ["python", "main.py"]
