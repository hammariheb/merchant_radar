FROM apache/airflow:2.9.1-python3.12

USER root
RUN apt-get update && apt-get install -y git && apt-get clean

USER airflow

RUN pip install --no-cache-dir --upgrade pip

# Install project dependencies 
RUN pip install --no-cache-dir \
    apache-airflow-providers-http==4.10.0 \
    google-cloud-bigquery==3.25.0 \
    db-dtypes==1.3.0 \
    openai==1.30.0 \
    httpx==0.27.0 \
    tqdm==4.66.0 \
    python-dotenv==1.0.0 \
    pandas==2.2.0 \
    beautifulsoup4==4.12.0 \
    langdetect==1.0.9 \
    plotly==5.22.0

RUN pip install --no-cache-dir \
    "dbt-bigquery==1.8.2" \
    "protobuf>=3.20.0,<5.0.0"
