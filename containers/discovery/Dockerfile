FROM python:3.11-slim
WORKDIR /app

# Copy this agent's specific requirements
COPY containers/discovery/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project code (relies on root build context)
COPY . .

# Ensure 'shared' and other root modules resolve
ENV PYTHONPATH=/app/backend:/app

# Discovery chat runs synchronously in the FastAPI backend (see backend/app/services/discovery_chat.py).
CMD ["python", "-c", "import sys; print('Discovery worker deprecated — use FastAPI /api/discovery/*', file=sys.stderr); sys.exit(0)"]
