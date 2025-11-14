FROM python:3.11-slim

# Install ALL dependencies including build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libxml2-dev \
    libsqlite3-dev \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    libpq-dev \
    libspatialite-dev \
    && ldconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from osgeo import gdal; print('✅ GDAL успешно установлен:', gdal.__version__)"
RUN python -c "from django.contrib.gis.gdal import GDALRaster; print('✅ Django GDAL работает')"

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]