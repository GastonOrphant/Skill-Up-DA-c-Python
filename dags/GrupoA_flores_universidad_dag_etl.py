import logging
from airflow import DAG
from airflow.decorators import task
from datetime import datetime, timedelta
from helper_functions import logger_setup
from helper_functions.extracting import extraction
from helper_functions.utils import *
import pandas as pd
import numpy as np
import csv
import boto3
import os
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.transfers.local_to_s3 import LocalFilesystemToS3Operator
from airflow.operators.python import PythonOperator

# Universidad
university = 'GrupoA_flores_universidad'

# Configuracion del logger
logger = logger_setup.logger_creation(university)

# Definimos el DAG
with DAG(f'{university}_dag_etl',
         default_args=default_args,
         catchup=False
         ) as dag:      
    
    # Extracción de Datos
    @task()
    def extract():
        logger.info('Inicio de proceso de extracción')
        try:
            extraction(university)
            logger.info("Se creo el csv con la información de la universidad")

        except Exception as e:
            logger.error(e)

    # Transformación de Datos
    @task()
    def transform():

        logger.info("Transforming data")
        
        df = pd.read_csv('files/GrupoA_flores_universidad_select.csv', index_col=0)
        df['university'] = df['university'].str.lower().str.replace('_',' ').str.strip()
        df['career'] = df['career'].str.lower().str.replace('_',' ').str.strip()
        df['first_name'] = df['first_name'].str.lower().str.replace('_',' ').str.strip().str.replace('(m[r|s]|[.])|(\smd\s)', '', regex=True)
        df['email'] = df['email'].str.lower().str.replace('_',' ').str.strip()
        df['gender'] = df['gender'].map({'F': 'female', 'M': 'male'})
        df['inscription_date'] = pd.to_datetime(df['inscription_date'], format='%Y/%m/%d')
        df['fecha_nacimiento'] = pd.to_datetime(df['fecha_nacimiento'])
        
        today = datetime.now()
        
        df['age'] = np.floor((today - df['fecha_nacimiento']).dt.days / 365)
        df['age'] = df['age'].apply(lambda x: x if (x > 18.0) and (x < 80) else -1)
        df['age'] = np.where(df['age']== -1, 21, df['age'])
        df['age'] = df['age'].astype(int)
        
        df = df.drop(columns='fecha_nacimiento')
        
        dfCod = pd.read_csv('assets/codigos_postales.csv',sep=',')
        dfCod = dfCod.drop_duplicates(['localidad'], keep='last')
            
        dfC = df['postal_code']
        dfL = df['location']
        dfC = dfC.dropna()
        dfL = dfL.dropna()
        TamC = dfC.size
        TamL = dfL.size

        if TamL == 0:
                df = pd.merge(df,dfCod,left_on='postal_code',right_on='codigo_postal')
                del df['codigo_postal']
                del df['location']
                df = df.rename(columns={'localidad':'location'})

        if TamC == 0:
                df = pd.merge(df,dfCod,left_on='location',right_on='localidad')
                del df['localidad']
                del df['postal_code']
                df = df.rename(columns={'codigo_postal':'postal_code'})
        
        
        df = df[['university', 'career', 'inscription_date', 'first_name', 'gender', 'age', 'postal_code', 'location', 'email']]
        
        df.to_csv('./datasets/GrupoA_flores_universidad_process.txt', sep='\t', index=False)
        
        logger.info("Data succesfully transformed")
        logger.info("Loading data to s3 bucket...")

    @task()
    def load(**kwargd):

        try:
            ACCESS_KEY = "AKIA2AY2D764PBLL5IPT"
            SECRET_ACCESS_KEY = "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"
            session = boto3.Session(
                aws_access_key_id=ACCESS_KEY,
                aws_secret_access_key=SECRET_ACCESS_KEY,
            )
            s3 = session.resource("s3")
            data = open("./datasets/GrupoA_flores_universidad_process.txt","rb")
            s3.Bucket("alkemy26").put_object(
                Key="GrupoA_flores_universidad_process.txt", Body=data
            )

            logging.info('Tarea de carga EXITOSA')
        except:
            logging.info('ERROR al cargar')

    
    extract() >> transform() >> load()

with DAG(
    "GrupoA_flores_universidad_dag_etl",
    start_date=datetime(2022, 12, 4),
    schedule_interval="@hourly",
    default_args={
        "retries": 5
    },
    catchup=False,
) as dag:

    extract = PythonOperator(
        task_id="extract",
        python_callable=extract
    )

    transform = PythonOperator(
        task_id="transform",
        python_callable = transform
    )

    load = PythonOperator(
        task_id="load",
        python_callable = load )
