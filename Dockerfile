FROM python:3.11-slim

# - no .pyc files in the image
# - unbuffered logs so Render/Docker show them immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Run as an unprivileged user: a compromised app must not own the container.
RUN chmod +x docker-entrypoint.sh \
    && useradd --create-home --shell /bin/sh appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
