FROM python:3.12-slim

WORKDIR /app

# Install system deps for opencv and h5py
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download Chronos-Bolt model at build time (optional, reduces cold start)
# RUN python -c "from chronos import ChronosBoltPipeline; ChronosBoltPipeline.from_pretrained('amazon/chronos-bolt-small')"

EXPOSE 8000 8501

CMD ["python", "src/api/main.py"]
