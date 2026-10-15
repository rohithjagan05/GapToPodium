# The Gap to the Podium API: a small image with only the serving code and results.
FROM python:3.11-slim

# Don't write .pyc files; print logs straight away.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Dependencies first, so Docker can reuse this layer when only code changes.
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Only the files the API reads.
COPY src/__init__.py src/config.py src/export.py src/api.py src/
COPY serving/ serving/

# Run as a normal user, not root.
RUN useradd --create-home appuser
USER appuser

# Hosts like Render set PORT; locally it defaults to 8000.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8000}"]