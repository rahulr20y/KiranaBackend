FROM python:3.10-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project files
COPY . .

# Create necessary directories with world-writable permissions
RUN mkdir -p /app/staticfiles /app/media && \
    chmod -R 777 /app/staticfiles /app/media

# Expose port
EXPOSE 8000

# Run migrations and collectstatic, then start daphne for ASGI/WebSocket support
CMD ["sh", "-c", "echo 'Running migrations...' && (python manage.py migrate --noinput || echo 'Migrations failed') && echo 'Collecting static files...' && (python manage.py collectstatic --noinput || echo 'Collectstatic failed') && echo 'Starting Daphne on port $PORT...' && daphne -b 0.0.0.0 -p $PORT kirana.asgi:application"]
