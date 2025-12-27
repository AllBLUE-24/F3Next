FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Set PYTHONPATH so the agent can find the 'shared' folder at root
ENV PYTHONPATH=/app:/app/shared
CMD ["python", "agents/health_check/worker.py"]