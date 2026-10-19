FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git libopenblas-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY app.py .
ENV PYTHONUNBUFFERED=1 HF_HOME=/cache/huggingface
ENTRYPOINT ["python", "app.py"]
