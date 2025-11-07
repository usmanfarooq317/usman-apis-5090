# Dockerfile - single-file Flask app, runs on port 5090
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5090
ENV APP_NAME=usman-apis-dashboard
ENV DOCKER_USER=usmanfarooq317
ENV IMAGE_NAME=usman-apis-dashboard
ENV VERSION=v1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy app
COPY app.py /app/app.py

EXPOSE 5090

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5090/api/health || exit 1

# Use gunicorn in production (4 workers)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5090", "app:app"]
