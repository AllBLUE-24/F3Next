# 1. Base Image
FROM python:3.11-slim

# 2. Set Environment
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /app

# 3. System Deps (for Postgres)
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 4. Install Dependencies (Merge both files)
COPY backend/requirements.txt ./requirements.backend.txt
COPY agents/requirements.txt ./requirements.agents.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.backend.txt \
    && pip install --no-cache-dir -r requirements.agents.txt

# 5. COPY CODE (The Magic Step)
# We copy both folders into the container so Python can see them both
COPY backend/ ./backend/
COPY agents/ ./agents/

# 6. Set PYTHONPATH
# This tells Python: "You can find modules in /app, /app/backend, and /app/agents"
ENV PYTHONPATH=/app:/app/backend:/app/agents

# 7. Run
EXPOSE 8000
# We run from the /app directory
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]