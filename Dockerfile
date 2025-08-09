FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

COPY . .

# Gunicorn config
ENV FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5000

EXPOSE 5000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"] 