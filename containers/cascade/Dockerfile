FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY containers/cascade/requirements.txt /app/cascade_requirements.txt
RUN pip install --no-cache-dir -r /app/cascade_requirements.txt

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PYTHONPATH=/app

CMD ["python", "-m", "containers.cascade.cascade_worker"]
