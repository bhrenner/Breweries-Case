from airflow import DAG
from datetime import datetime
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.email_operator import EmailOperator
from airflow.models import Variable
from utils import AdditionalFunctions
import pandas as pd
import pyarrow.parquet as pq
import sys
import os

scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'dags')
sys.path.append(scripts_dir)


def agg_by_loc_type(ti):
    # Retrieve the file path from the Airflow variable
    file_path = Variable.get("path_silver")

    # Print the received path for debugging
    print(f"Received Path: {file_path}")

    # Check if the file path exists
    if file_path and os.path.exists(file_path):
        # Get the current date
        dt = datetime.now()

        # Lista para armazenar os DataFrames agregados de cada país
        dfs = []

        # Carregar o dataset particionado e obter a lista de valores únicos na coluna 'pais'
        data = pq.ParquetDataset(file_path, use_legacy_dataset=False)

        print(data.fragments)
        for partition in data.fragments:
            # Ler a partição específica como um PyArrow Table
            table = partition.to_table()
            df = table.to_pandas()
            part = (str(partition).split('/')[4]).split('=')[1]
            df['country'] = part
            df_agg = (
                df.groupby(['country', 'state', 'city', 'brewery_type'])['id']
                .count().reset_index(name='number_of_breweries')
            )

            # Adicionar o DataFrame agregado à lista
            dfs.append(df_agg)

        # Concatenar todos os DataFrames agregados em um único DataFrame final
        dfFinal = pd.concat(dfs, ignore_index=True)

        # Process the date in the aggregated DataFrame
        dfFinal = AdditionalFunctions.process_date(dfFinal)

        # Define the path and filename for the aggregated data
        path = "datalake/gold/BreweriesbyLocType"

        # Ensure the directory exists
        AdditionalFunctions.ensure_directory_exists(file_path)

        # Save the aggregated DataFrame as a parquet file with partitioning
        dfFinal.to_parquet(path, partition_cols=[
            'process_date'], compression='gzip')

        # Set the Airflow variable with the path of the parquet file
        # Variable.set("path_gold", file_path)

    else:
        # Raise an error if the file is not found
        raise FileNotFoundError(f"Silver File Not Found: {file_path}")


with DAG(
    'AggBreweriesToGold',
    schedule_interval='@daily',
    catchup=False,
    start_date=datetime.now()
) as dag:

    aggBeweries = PythonOperator(
        task_id='aggBeweries',
        python_callable=agg_by_loc_type
    )

aggBeweries
