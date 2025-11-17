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

# Copy alembic configuration (explicit)
COPY alembic.ini .
COPY alembic/ ./alembic/

# Copy reset script
COPY reset_alembic.py .

# Copy application code
COPY server/ ./server/

# Copy any other necessary files (if .env exists)
COPY .env* ./ 

# Create directory for generated PDFs
RUN mkdir -p /app/generated_pdfs && chmod 777 /app/generated_pdfs

# Expose port
EXPOSE 8000

# Start command (will be overridden by railway.json)
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]