# Dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System dependencies for:
# - building Python packages (build-essential)
# - Pillow (libjpeg-dev, zlib1g-dev, libpng-dev)
# - some ML/image libs, OpenCV, etc. (libglib2.0-0, libsm6, libxext6, libxrender1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# In production you usually drop --reload, but okay for dev in Docker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
