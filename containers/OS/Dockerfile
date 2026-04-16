FROM python:3.11-slim
WORKDIR /app

# Copy this agent's specific requirements
COPY containers/OS/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project code (relies on root build context)
COPY . .

# Ensure 'shared' and other root modules resolve
ENV PYTHONPATH=/app

CMD ["python", "containers/os/os_worker.py"]
