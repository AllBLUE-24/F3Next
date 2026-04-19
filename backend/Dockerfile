FROM python:3.11-slim

WORKDIR /app

# Ensure we have the latest pip
RUN pip install --upgrade pip

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything into the container
COPY . .

# IMPORTANT: Set PYTHONPATH so app can find sibling directories like 'agents'
ENV PYTHONPATH=/app/backend:/app

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
