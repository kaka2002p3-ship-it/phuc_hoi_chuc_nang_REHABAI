FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and MediaPipe, and curl for healthcheck
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt /app/requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend code
COPY backend/ /app/backend/
# Copy shared code (needed for inference preprocessing)
COPY shared/ /app/shared/
COPY migrations/ /app/migrations/
COPY alembic.ini /app/alembic.ini
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create data directory for SQLite
RUN mkdir -p /app/data

ENV PYTHONPATH="/app"

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
