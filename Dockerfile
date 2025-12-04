FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libxml2-dev \
    libsqlite3-dev \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    libpq-dev \
    libspatialite-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from osgeo import gdal; print('GDAL version:', gdal.__version__)"
RUN python -c "from django.contrib.gis.gdal import GDALRaster; print('Django GDAL backend is ready')"

COPY . .
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /app/staticfiles /app/media && chown -R app:app /app

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]