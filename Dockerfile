# Agent Edu — giao diện web (FastAPI + Uvicorn)
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

WORKDIR /app

# Pillow / ảnh minh họa: thư viện hệ thống tối thiểu
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        libpng16-16 \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY cham_bai ./cham_bai/

RUN python -m pip install --upgrade pip \
    && pip install --prefer-binary --timeout 120 --retries 10 .

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

EXPOSE 8765

USER appuser

# 0.0.0.0 để truy cập từ máy host qua cổng đã publish (dev: 1 worker; prod dùng compose override --workers)
CMD ["uvicorn", "cham_bai.web_app:app", "--host", "0.0.0.0", "--port", "8765"]
