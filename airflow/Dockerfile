FROM apache/airflow:2.9.2-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

USER airflow
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    dbt-core \
    dbt-postgres \
    sqlalchemy \
    psycopg2-binary \
    prometheus-client \
    pydantic-settings

