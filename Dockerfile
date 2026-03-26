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

# Run migrations and collectstatic, then start gunicorn
# Use the PORT environment variable provided by Render
# We use '|| true' to ensure the container starts even if migrations or static collection fails,
# which allows us to access diagnostic endpoints
CMD ["sh", "-c", "echo 'Running migrations...' && (python manage.py migrate --noinput || echo 'Migrations failed') && echo 'Collecting static files...' && (python manage.py collectstatic --noinput || echo 'Collectstatic failed') && echo 'Starting Gunicorn on port $PORT...' && gunicorn kirana.wsgi:application --bind 0.0.0.0:$PORT --workers 4"]
