FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    logrotate \
    supervisor \
    curl && \
    pip install --no-cache-dir poetry && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md /app/

RUN poetry config virtualenvs.create false && \
    poetry install --with dev --no-root

COPY floor_predictor_api /app/floor_predictor_api

RUN pip install .

COPY logrotate.conf /etc/logrotate.d/app
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["supervisord", "-n"]
