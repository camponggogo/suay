FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git libopenblas-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY auto_agent.py dashboard.html ./
ENV PYTHONUNBUFFERED=1 HF_HOME=/cache/huggingface
EXPOSE 8080/tcp 31337/tcp 31338/udp 31339/tcp
CMD ["python", "auto_agent.py"]
