FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-dev.lock ./
RUN pip install --require-hashes -r requirements-dev.lock

COPY . .
RUN pip install --no-deps --no-build-isolation -e .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
