import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.models import Variable
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from utils import AdditionalFunctions

api_endpoint = Variable.get("endpoint_api")

# Request Api Content


def get_api_content(api_endpoint):
    pg = 1
    breweriesDF = pd.DataFrame()
    print(api_endpoint)

    while True:
        params = {'page': pg, 'per_page': 200}

        resp = requests.request('GET', url=api_endpoint, params=params)
        breweries = resp.json()
        if len(breweries) > 0:
            breweriesDF = pd.concat([breweriesDF, pd.DataFrame(breweries)])
            pg += 1
        else:
            break

    return breweriesDF.reset_index(drop=True)


def processing_api_json(ti):

    d = get_api_content(api_endpoint)

    if df.empty:
        raise ValueError('API retornou dados vazios')

    format_dt = datetime.now().strftime('%Y%m%d')
    filename = f"breweries_{format_dt}.json"
    path = "datalake/bronze/"
    file_path = path + filename

    AdditionalFunctions.ensure_directory_exists(file_path)

    # Write DataFrame JSON
    df.to_json(file_path, orient='records', lines=True)

    # Set Airflow Variable
    Variable.set("path_bronze", file_path)

    return file_path


default_args = {
    'owner': 'airflow',
    'start_date': datetime.now(),
    'retries': 2,
    'retry_delay': timedelta(seconds=5),
    'on_failure_callback': AdditionalFunctions.email_status,
    'on_retry_callback': AdditionalFunctions.email_status
}

with DAG(
    'extractAPItoBronze',
    schedule_interval='@daily',
    catchup=False,
    default_args=default_args
) as dag:

    api_available = HttpSensor(
        task_id='api_available',
        http_conn_id='api',
        endpoint="breweries"
    )

    get_api = PythonOperator(
        task_id='get_api',
        python_callable=processing_api_json,
        provide_context=True
    )

    triggerDagToSilver = TriggerDagRunOperator(
        task_id='triggerDagToSilver',
        trigger_dag_id='TransformToSilver'
    )

api_available >> get_api >> triggerDagToSilver
