import pandas as pd
from pandas import json_normalize
import os
from datetime import datetime, timedelta
import re
import unicodedata
import smtplib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from airflow.utils.email import send_email


def clean_columns(df):
    df.columns = (
        df.columns
        .str.lower()         # Convert column names to lowercase
        .str.replace(' ', '_')  # Replace spaces with underscores
        .str.strip()         # Remove leading and trailing whitespace
    )
    return df


def clean_partitions(s):
    if isinstance(s, str):
        s = s.strip()  # Remove espaços extras no início e no final

        # Normaliza o texto para decompor os caracteres acentuados e remover acentos, mantendo o hífen
        s = unicodedata.normalize('NFKD', s)

        # Remove os diacríticos (acentos, trema) mantendo a letra
        s = ''.join(c for c in s if not unicodedata.combining(c))

        # Substitui espaços internos por underscores
        s = s.replace(" ", "_")

        # Remove caracteres especiais, mantendo letras, números, hífen e underscores
        s = re.sub(r'[^A-Za-z0-9_-]', '', s)

    return s

# Function to create directory if it doesn't exist


def ensure_directory_exists(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        print("Creating directory")
        os.makedirs(directory)


# Function to add a processing date column to a DataFrame
def process_date(df):
    # Get the current date in 'YYYYMMDD' format
    format_dt = datetime.now().strftime('%Y%m%d')
    # Add the processing date column
    df['process_date'] = format_dt
    return df


def name_repair(field):
    ajustes = {
        'Krnten': 'Karnten',
        'Niedersterreich': 'Niederosterreich',
        # 'Caf Okei': 'Cafe Okei',
        'Klagenfurt am Wrthersee': 'Klagenfurt am Worthersee'
    }

    if field in ajustes:
        return ajustes[field]
    else:
        return field


def descript_pass():
    chave = b"12345678901234567890123456789012"
    iv = b"abcdefghijklmnop"
    try:
        with open('password.txt', "rb") as f:
            iv = f.read(16)
            ciphertext = f.read()

        if len(ciphertext) == 0:
            raise ValueError(
                "Arquivo de criptografia está vazio ou corrompido.")

        cipher = Cipher(algorithms.AES(chave), modes.CBC(iv),
                        backend=default_backend())
        decryptor = cipher.decryptor()
        senha_padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        senha = unpadder.update(senha_padded) + unpadder.finalize()
        return palavra_original.decode()
    except ValueError as e:
        print("Erro ao remover padding:", e)
        return None
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return None


def email_status(context):
    task_instance = context.get('task_instance')
    task_id = task_instance.task_id
    dag_id = task_instance.dag_id
    exception = context.get('exception')
    retries = task_instance.try_number  # Quantas tentativas já foram feitas
    max_retries = task_instance.max_tries  # Número máximo de tentativas

    # Mensagem customizada sobre a falha
    if retries >= max_retries:
        # Caso a tarefa tenha falhado todas as tentativas
        mensagem = f"A tarefa {task_id} na DAG {dag_id} falhou após {retries} tentativas. Erro: {exception}"
    else:
        # Caso a tarefa tenha falhado, mas ainda tenha tentativas restantes
        mensagem = f"A tarefa {task_id} na DAG {dag_id} falhou na tentativa {retries}. Erro: {exception}"

    subject = "Relatório de Status das DAGs"
    # Get the status message from the previous task
    body = mensagem  # ti.xcom_pull(task_ids='statusDag')
    recipient = 'breweriescase@hotmail.com'

    password = descript_pass()
    print(password)
    # msg = MIMEText(body)
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = 'breweriescase@hotmail.com'
    msg['To'] = recipient

    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP('smtp-mail.outlook.com', 587) as server:
            server.ehlo()  # Identify the server
            server.starttls()  # Start TLS
            server.ehlo()  # Re-identify the server after starting TLS
            server.login('breweriescase@hotmail.com', password)
            server.sendmail(msg['From'], [msg['To']], msg.as_string())

            print("E-mail enviado com sucesso!")

    except Exception as e:
        print(f"Falha ao enviar o e-mail: {e}")
        # Send an email indicating the failure to send the report
        airflow.utils.email.send_email(
            'breweriescase@hotmail.com', 'Airflow TEST HERE', 'This is airflow status success')
