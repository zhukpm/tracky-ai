FROM python:3.12-slim

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    TERM=linux \
    HOME=/root \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app:${PYTHONPATH}

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt && \
    rm -f requirements.txt && \
    rm -rf $HOME/.cache && \
    pip check

COPY trackyai trackyai

CMD ["python", "trackyai/__init__.py"]
