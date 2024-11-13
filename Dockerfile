FROM apache/airflow:2.9.0-python3.12

# Set environment variables
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-arm64

# Use root user to install system dependencies
USER root

# Update apt-get, install dependencies, clean up apt cache
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        openjdk-11-jdk && \
    rm -rf /var/lib/apt/lists/*

# Switch back to airflow user and set up Python dependencies
USER airflow

# Upgrade pip, clear cache, and install required Python packages with specific versions
RUN pip cache purge && \
    pip install --upgrade pip && \
    pip uninstall -y apache-airflow-providers-openlineage && \
    pip install --no-cache-dir \
        apache-airflow==2.7.1 \
        apache-airflow-providers-apache-spark \
        pyspark==3.5.3 \
        -r requirements.txt        
