# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including LibreOffice
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libreoffice \
    libreoffice-writer \
    libreoffice-core \
    fonts-liberation \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for generated PDFs (fallback if volume not mounted)
RUN mkdir -p /app/generated_pdfs && chmod 777 /app/generated_pdfs
RUN mkdir -p /data/uploads/pdfs && chmod 777 /data/uploads/pdfs || true

# Expose port
EXPOSE 8000



# Run migrations then start server
CMD alembic upgrade head && uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}