from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from datetime import datetime, timedelta
import json
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
import boto3
import os

def download_from_s3(bucket_name, s3_key, local_path):
    """
    Download a file from AWS S3 to a local path
    """
    try:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Download the file
        s3_client.download_file(bucket_name, s3_key, local_path)
        print(f"Successfully downloaded {s3_key} from {bucket_name} to {local_path}")
        return local_path
    except Exception as e:
        print(f"Error downloading file from S3: {e}")
        raise

def download_hotel_data(**context):
    """
    Download hotel data from S3 bucket specified in DAG configuration
    """
    # Get S3 path from DAG configuration
    hotel_s3_bucket = context['dag_run'].conf.get('hotel_s3_bucket', 'default-bucket')
    hotel_s3_key = context['dag_run'].conf.get('hotel_s3_key', 'hotelsdata.json')
    
    # Local path to save the downloaded file
    local_path = f'/tmp/{hotel_s3_key}'
    
    # Download the file
    download_path = download_from_s3(hotel_s3_bucket, hotel_s3_key, local_path)
    
    # Return the local path for use in subsequent tasks
    return download_path

def process_hotel_data(**context):
    """
    Process the hotel JSON data from the downloaded file
    """
    # Get the local path of the downloaded file
    json_file_path = context['task_instance'].xcom_pull(task_ids='download_hotel_data')
    
    try:
        # Read and parse the JSON file
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Determine the data structure
        if isinstance(data, dict) and "data" in data:
            hotels_list = data.get("data", [])
        elif isinstance(data, list):
            hotels_list = data
        else:
            print(f"Unexpected JSON structure: {type(data)}")
            hotels_list = []
            
        print(f"Processing {len(hotels_list)} hotel entries")
        
        # Process the data into a list of dictionaries
        processed_data = []
        for hotel in hotels_list:
            if not isinstance(hotel, dict):
                continue
                
            hotel_data = {
                "chain_code": hotel.get("chainCode"),
                "iata_code": hotel.get("iataCode"),
                "dupe_id": hotel.get("dupeId"),
                "name": hotel.get("name"),
                "hotel_id": hotel.get("hotelId"),
                "latitude": hotel.get("geoCode", {}).get("latitude"),
                "longitude": hotel.get("geoCode", {}).get("longitude"),
                "country_code": hotel.get("address", {}).get("countryCode"),
                "distance_value": hotel.get("distance", {}).get("value"),
                "distance_unit": hotel.get("distance", {}).get("unit"),
                "last_update": hotel.get("lastUpdate"),
                "is_sponsored": hotel.get("retailing", {}).get("sponsorship", {}).get("isSponsored", False)
            }
            processed_data.append(hotel_data)
        
        print(f"Successfully processed {len(processed_data)} hotel entries")
        return json.dumps(processed_data)
        
    except Exception as e:
        print(f"Error processing hotel data: {e}")
        return json.dumps([])

def download_attractions_data(**context):
    """
    Download attractions data from S3 bucket specified in DAG configuration
    """
    # Get S3 path from DAG configuration
    attractions_s3_bucket = context['dag_run'].conf.get('attractions_s3_bucket', 'default-bucket')
    attractions_s3_key = context['dag_run'].conf.get('attractions_s3_key', 'attractionsdata.json')
    
    # Local path to save the downloaded file
    local_path = f'/tmp/{attractions_s3_key}'
    
    # Download the file
    download_path = download_from_s3(attractions_s3_bucket, attractions_s3_key, local_path)
    
    # Return the local path for use in subsequent tasks
    return download_path

def read_attractions_data(**context):
    """
    Read attractions data from the downloaded file
    """
    # Get the local path of the downloaded file
    json_file_path = context['task_instance'].xcom_pull(task_ids='download_attractions_data')
    
    # Read and return the JSON file contents
    with open(json_file_path, 'r') as f:
        return json.dumps(json.load(f))

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

hotelDag = DAG(
    'load_hotel_to_snowflake',
    default_args=default_args,
    description='Load hotel data to Snowflake',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2025, 4, 1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=60),
    default_view='graph',
    tags=['hotel', 'snowflake', 'etl'],
) 

# Create database in Snowflake
init_database = SnowflakeOperator(
    task_id='init_database',
    snowflake_conn_id='snowflake_conn',
    sql="""
    USE ROLE ACCOUNTADMIN;
    USE WAREHOUSE COMPUTE_WH;
    CREATE DATABASE IF NOT EXISTS HOTEL_PROJECT;
    USE DATABASE HOTEL_PROJECT;
    CREATE SCHEMA IF NOT EXISTS PUBLIC;
    USE SCHEMA PUBLIC;
    """,
    dag=hotelDag
)

# Create hotels table
create_hotels_table = SnowflakeOperator(
    task_id='create_hotels_table',
    snowflake_conn_id='snowflake_conn',
    sql="""
    USE WAREHOUSE COMPUTE_WH;
    USE DATABASE HOTEL_PROJECT;
    USE SCHEMA PUBLIC;
    
    -- Create the main table
    CREATE TABLE IF NOT EXISTS hotels (
        chain_code VARCHAR,
        iata_code VARCHAR,
        dupe_id NUMBER,
        name VARCHAR,
        hotel_id VARCHAR,
        latitude FLOAT,
        longitude FLOAT,
        country_code VARCHAR,
        distance_value FLOAT,
        distance_unit VARCHAR,
        last_update TIMESTAMP_NTZ,
        is_sponsored BOOLEAN,
        load_date TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP
    );
    """,
    dag=hotelDag
)

# Create attractions table
create_attractions_table = SnowflakeOperator(
    task_id='create_attractions_table',
    snowflake_conn_id='snowflake_conn',
    sql="""
    USE WAREHOUSE COMPUTE_WH;
    USE DATABASE HOTEL_PROJECT;
    USE SCHEMA PUBLIC;
    
    -- Create the attractions table
    CREATE TABLE IF NOT EXISTS attractions (
        attraction_id VARCHAR,
        name VARCHAR,
        hotel_id VARCHAR,
        distance_value FLOAT,
        distance_unit VARCHAR,
        attraction_type VARCHAR,
        load_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    dag=hotelDag
)

# Download data from S3
download_hotel_data = PythonOperator(
    task_id='download_hotel_data',
    python_callable=download_hotel_data,
    provide_context=True,
    dag=hotelDag
)

download_attractions_data = PythonOperator(
    task_id='download_attractions_data',
    python_callable=download_attractions_data,
    provide_context=True,
    dag=hotelDag
)

# Process hotel data
process_hotel_json = PythonOperator(
    task_id='process_hotel_json',
    python_callable=process_hotel_data,
    provide_context=True,
    dag=hotelDag
)

# Read attractions data
read_attractions_json = PythonOperator(
    task_id='read_attractions_json',
    python_callable=read_attractions_data,
    provide_context=True,
    dag=hotelDag
)

# Load hotel data to Snowflake
load_hotel_data = SnowflakeOperator(
    task_id='load_hotel_data',
    snowflake_conn_id='snowflake_conn',
    sql="""
    USE WAREHOUSE COMPUTE_WH;
    USE DATABASE HOTEL_PROJECT;
    USE SCHEMA PUBLIC;
    
    -- Transform and load into hotels table
    INSERT INTO hotels (
        chain_code,
        iata_code,
        dupe_id,
        name,
        hotel_id,
        latitude,
        longitude,
        country_code,
        distance_value,
        distance_unit,
        last_update,
        is_sponsored
    )
    WITH json_data AS (
        SELECT PARSE_JSON('{{ task_instance.xcom_pull(task_ids="process_hotel_json") }}') as json
    )
    SELECT DISTINCT
        f.value:chain_code::VARCHAR as chain_code,
        f.value:iata_code::VARCHAR as iata_code,
        f.value:dupe_id::NUMBER as dupe_id,
        f.value:name::VARCHAR as name,
        f.value:hotel_id::VARCHAR as hotel_id,
        f.value:latitude::FLOAT as latitude,
        f.value:longitude::FLOAT as longitude,
        f.value:country_code::VARCHAR as country_code,
        f.value:distance_value::FLOAT as distance_value,
        f.value:distance_unit::VARCHAR as distance_unit,
        TO_TIMESTAMP_NTZ(f.value:last_update::VARCHAR) as last_update,
        f.value:is_sponsored::BOOLEAN as is_sponsored
    FROM json_data,
    LATERAL FLATTEN(input => json) f;
    """,
    dag=hotelDag
)

# Load attractions data to Snowflake
load_attractions_data = SnowflakeOperator(
    task_id='load_attractions_data',
    snowflake_conn_id='snowflake_conn',
    sql="""
    USE WAREHOUSE COMPUTE_WH;
    USE DATABASE HOTEL_PROJECT;
    USE SCHEMA PUBLIC;
    
    -- Transform and load into attractions table
    INSERT INTO attractions (
        attraction_id,
        name,
        hotel_id,
        distance_value,
        distance_unit,
        attraction_type
    )
    WITH json_data AS (
        SELECT PARSE_JSON('{{ task_instance.xcom_pull(task_ids="read_attractions_json") }}') as json
    )
    SELECT DISTINCT
        a.value:id::VARCHAR as attraction_id,
        a.value:name::VARCHAR as name,
        a.value:hotel_id::VARCHAR as hotel_id,
        a.value:distance:value::FLOAT as distance_value,
        a.value:distance:unit::VARCHAR as distance_unit,
        a.value:type::VARCHAR as attraction_type
    FROM json_data,
    LATERAL FLATTEN(input => json:attractions) a;
    """,
    dag=hotelDag
)

# Add a task to log completion
completion_log = BashOperator(
    task_id='completion_log',
    bash_command='echo "Hotel data pipeline completed successfully"',
    dag=hotelDag,
    trigger_rule='none_failed'
)

# Set task dependencies
init_database >> [create_hotels_table, create_attractions_table]
create_hotels_table >> download_hotel_data >> process_hotel_json >> load_hotel_data
create_attractions_table >> download_attractions_data >> read_attractions_json >> load_attractions_data
[load_hotel_data, load_attractions_data] >> completion_log

# This exposes the DAG
hotelDag