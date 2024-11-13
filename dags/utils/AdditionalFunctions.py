from datetime import datetime, timedelta
import re
import unicodedata
import smtplib
import re
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from airflow.utils.email import send_email
from email.mime.text import MIMEText
import smtplib


def clean_columns(df):
    df.columns = (
        df.columns
        # Convert column names to lowercase
        .str.lower()
         # Replace spaces with underscores
        .str.replace(' ', '_') 
        # Remove leading and trailing whitespace
        .str.strip()         
    )
    return df

# Function to clean and format a string
def clean_partitions(s):
    if isinstance(s, str):
        s = s.strip()  # Remove leading/trailing spaces
        # Normalize text to decompose accented characters and remove accents
        s = unicodedata.normalize('NFKD', s)
        # Remove diacritics (accents, umlauts) while keeping the base letter
        s = ''.join(c for c in s if not unicodedata.combining(c))
        # Replace internal spaces with underscores
        s = s.replace(" ", "_")
        # Remove special characters while preserving letters, numbers, hyphens, and underscores
        s = re.sub(r'[^A-Za-z0-9_-]', '', s)
    return s

# Function to ensure the existence of a directory
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

# Function to repair certain string field values
def name_repair(field):
    ajustes = {
        'Krnten': 'Karnten',
        'Niedersterreich': 'Niederosterreich',
        'Klagenfurt am Wrthersee': 'Klagenfurt am Worthersee'
    }
    # Return the repaired value if found, otherwise return the original field
    if field in ajustes:
        return ajustes[field]
    else:
        return field

# Function to decrypt the password stored in a file


def descript_pass():
    chave = b"12345678901234567890123456789012"  # AES key
    iv = b"abcdefghijklmnop"  # Initialization vector
    file_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'password.txt')
    try:
        # Read the encrypted data from the file
        with open(file_path, "rb") as f:
            iv = f.read(16)
            ciphertext = f.read()
            
        if len(ciphertext) == 0:
            raise ValueError("Encryption file is empty or corrupted.")

        # Set up the AES cipher for CBC mode
        cipher = Cipher(algorithms.AES(chave), modes.CBC(iv),
                        backend=default_backend())
        decryptor = cipher.decryptor()

        # Decrypt the password and remove padding
        senha_padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        senha = unpadder.update(senha_padded) + unpadder.finalize()
       
        # Return the decrypted password as a string
        return senha.decode('utf-8')
    except ValueError as e:
        print("Error removing padding:", e)
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Function to send an email with task failure details


def email_status(context):
    task_instance = context.get('task_instance')
    task_id = task_instance.task_id
    dag_id = task_instance.dag_id
    exception = context.get('exception')
    retries = task_instance.try_number
    max_retries = task_instance.max_tries

    # Construct the failure message based on retries
    if retries >= max_retries:
        mensagem = f"The task {task_id} in DAG {dag_id} failed after {retries} attempts. Error: {exception}"
    else:
        mensagem = f"The task {task_id} in DAG {dag_id} failed on attempt {retries}. Error: {exception}"

    subject = "DAG Status Report"
    body = mensagem  # Body message containing failure details
    recipient = 'breweriescase@hotmail.com'

    # Get the decrypted password
    password = descript_pass()

    # Create the email message
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = 'breweriescase@hotmail.com'
    msg['To'] = recipient
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Send the email using SMTP
        with smtplib.SMTP('smtp-mail.outlook.com', 587) as server:
            server.ehlo()  # Identify the server
            server.starttls()  # Start TLS encryption
            server.ehlo()  # Re-identify after starting TLS
            # Login with the decrypted password
            server.login('breweriescase@hotmail.com', password)
            server.sendmail(msg['From'], [msg['To']],
                            msg.as_string())  # Send the email

            print("Email sent successfully!")

    except Exception as e:
        print(f"Failed to send email: {e}")
