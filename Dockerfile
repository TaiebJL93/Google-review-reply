# Image for hosting ReviewReply on Cloudflare Containers (see cloudflare/ and
# README "Hosting on Cloudflare"). Cloudflare requires linux/amd64 images.
FROM --platform=linux/amd64 python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Runs as an unprivileged user; the app only needs to read its own code.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# --proxy-headers: trust X-Forwarded-Proto from the Worker in front, so
# request.url reports https. The container is only reachable through that Worker.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
