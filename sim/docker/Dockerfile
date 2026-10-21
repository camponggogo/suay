FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/versions/python:/app/sim:/app/sim/docker

WORKDIR /app

COPY sim/docker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Real control plane + the policy and mock modules used by the fleet simulation.
COPY versions/python/control /app/versions/python/control
COPY sim/token_policy.py /app/sim/token_policy.py
COPY sim/mock_upstream.py /app/sim/mock_upstream.py
COPY sim/docker /app/sim/docker

WORKDIR /app/sim/docker

CMD ["python", "node_agent.py"]
