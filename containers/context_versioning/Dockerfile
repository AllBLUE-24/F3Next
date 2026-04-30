FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY containers/context_versioning/requirements.txt /app/cvs_requirements.txt
RUN pip install --no-cache-dir -r /app/cvs_requirements.txt

# Root requirements (llm_router, shared_llm, etc.)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Source
COPY . /app

ENV PYTHONPATH=/app

CMD ["python", "-m", "containers.context_versioning.cvs_worker"]
