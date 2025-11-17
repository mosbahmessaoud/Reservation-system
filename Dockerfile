FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libreoffice \
    libreoffice-writer \
    libreoffice-core \
    fonts-liberation \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy alembic files
COPY alembic.ini .
COPY alembic/ ./alembic/

# Copy application
COPY server/ ./server/

RUN mkdir -p /app/generated_pdfs && chmod 777 /app/generated_pdfs

EXPOSE 8000

# Your main.py handles migrations automatically
CMD ["python", "-m", "server.main"]