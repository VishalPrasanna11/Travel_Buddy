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

def read_json_file(file_path):
    with open(file_path, 'r') as f:
        return json.dumps(json.load(f))

def process_daily_flights_data(**context):
    json_data = context['task_instance'].xcom_pull(task_ids='read_daily_json')
    data = json.loads(json_data)
    
    # Process the data into a list of dictionaries
    processed_data = []
    for itinerary in data.get("data", {}).get("itineraries", []):
        for leg in itinerary.get("legs", []):
            for carrier in leg.get("carriers", {}).get("marketing", []):
                for segment in leg.get("segments", []):
                    processed_data.append({
                        "flight_id": itinerary.get("id"),
                        "price_raw": itinerary.get("price", {}).get("raw"),
                        "price_formatted": itinerary.get("price", {}).get("formatted"),
                        "origin_id": leg.get("origin", {}).get("id"),
                        "destination_id": leg.get("destination", {}).get("id"),
                        "departure_time": leg.get("departure"),
                        "arrival_time": leg.get("arrival"),
                        "airline_name": carrier.get("name"),
                        "flight_number": segment.get("flightNumber")
                    })
    
    return json.dumps(processed_data)

def process_and_load_daily_flights(**context):
    # Get the JSON data
    json_data = context['task_instance'].xcom_pull(task_ids='read_daily_json')
    data = json.loads(json_data)
    
    # Process the data into a list of dictionaries
    processed_data = []
    for itinerary in data.get("data", {}).get("itineraries", []):
        for leg in itinerary.get("legs", []):
            for carrier in leg.get("carriers", {}).get("marketing", []):
                for segment in leg.get("segments", []):
                    processed_data.append({
                        "flight_id": itinerary.get("id"),
                        "price_raw": itinerary.get("price", {}).get("raw"),
                        "price_formatted": itinerary.get("price", {}).get("formatted"),
                        "origin_id": leg.get("origin", {}).get("id"),
                        "destination_id": leg.get("destination", {}).get("id"),
                        "departure_time": leg.get("departure"),
                        "arrival_time": leg.get("arrival"),
                        "airline_name": carrier.get("name"),
                        "flight_number": segment.get("flightNumber")
                    })
    
    # Convert to DataFrame
    df = pd.DataFrame(processed_data)
    
    # Use SnowflakeHook to get connection
    hook = SnowflakeHook(snowflake_conn_id='snowflake_conn')
    
    # Write to Snowflake using the hook
    hook.insert_rows(
        table='DAILY_FLIGHTS',
        rows=df.values.tolist(),
        target_fields=df.columns.tolist()
    )

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

extractDag = DAG(
    'load_to_snowflake',
    default_args=default_args,
    description='Load data to Snowflake',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
) 

# Create table in Snowflake
init_database = SnowflakeOperator(
    task_id='init_database',
    snowflake_conn_id='snowflake_conn',
    sql="""
    USE ROLE ACCOUNTADMIN;
    USE WAREHOUSE COMPUTE_WH;
    CREATE DATABASE IF NOT EXISTS FINAL_PROJECT;
    USE DATABASE FINAL_PROJECT;
    CREATE SCHEMA IF NOT EXISTS PUBLIC;
    USE SCHEMA PUBLIC;
    """,
    dag=extractDag
)

# Create daily flights table
create_daily_flights_table = SnowflakeOperator(
    task_id='create_daily_flights_table',
    snowflake_conn_id='snowflake_conn',
    sql="""
    USE WAREHOUSE COMPUTE_WH;
    USE DATABASE FINAL_PROJECT;
    USE SCHEMA PUBLIC;
    
    -- Drop the table if it exists to ensure clean state
    
    -- Create the main table
    CREATE TABLE IF NOT EXISTS daily_flights (
        flight_id VARCHAR,
        price_raw FLOAT,
        price_formatted VARCHAR,
        origin_id VARCHAR,
        destination_id VARCHAR,
        departure_time TIMESTAMP_NTZ,
        arrival_time TIMESTAMP_NTZ,
        airline_name VARCHAR,
        flight_number VARCHAR,
        load_date TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP
    );
    """,
    dag=extractDag
)

# Create monthly flights table
create_monthly_flights_table = SnowflakeOperator(
    task_id='create_monthly_flights_table',
    snowflake_conn_id='snowflake_conn',
    sql="""
    USE WAREHOUSE COMPUTE_WH;
    USE DATABASE FINAL_PROJECT;
    USE SCHEMA PUBLIC;
    
    -- Create the main table if it doesn't exist
    CREATE TABLE IF NOT EXISTS monthly_flights (
        flight_id VARCHAR,
        price_raw FLOAT,
        price_formatted VARCHAR,
        origin_id VARCHAR,
        destination_id VARCHAR,
        departure_time TIMESTAMP,
        arrival_time TIMESTAMP,
        airline_name VARCHAR,
        flight_number VARCHAR,
        load_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    dag=extractDag
)

# Read daily flights JSON
read_daily_json = PythonOperator(
    task_id='read_daily_json',
    python_callable=read_json_file,
    op_kwargs={'file_path': '/opt/airflow/data/data3.json'},
    dag=extractDag
)

# Read monthly flights JSON
read_monthly_json = PythonOperator(
    task_id='read_monthly_json',
    python_callable=read_json_file,
    op_kwargs={'file_path': '/opt/airflow/data/data2.json'},
    dag=extractDag
)

# Process daily flights data
process_daily_json = PythonOperator(
    task_id='process_daily_json',
    python_callable=process_daily_flights_data,
    provide_context=True,
    dag=extractDag
)

# Load daily flights data
load_daily_flights = SnowflakeOperator(
    task_id='load_daily_flights',
    snowflake_conn_id='snowflake_conn',
    sql="""
    USE WAREHOUSE COMPUTE_WH;
    USE DATABASE FINAL_PROJECT;
    USE SCHEMA PUBLIC;
    
    -- Transform and load into final table
    INSERT INTO daily_flights (
        flight_id,
        price_raw,
        price_formatted,
        origin_id,
        destination_id,
        departure_time,
        arrival_time,
        airline_name,
        flight_number
    )
    WITH json_data AS (
        SELECT PARSE_JSON('{{ task_instance.xcom_pull(task_ids="process_daily_json") }}') as json
    )
    SELECT DISTINCT
        f.value:flight_id::VARCHAR as flight_id,
        f.value:price_raw::FLOAT as price_raw,
        f.value:price_formatted::VARCHAR as price_formatted,
        f.value:origin_id::VARCHAR as origin_id,
        f.value:destination_id::VARCHAR as destination_id,
        TO_TIMESTAMP_NTZ(f.value:departure_time::VARCHAR) as departure_time,
        TO_TIMESTAMP_NTZ(f.value:arrival_time::VARCHAR) as arrival_time,
        f.value:airline_name::VARCHAR as airline_name,
        f.value:flight_number::VARCHAR as flight_number
    FROM json_data,
    LATERAL FLATTEN(input => json) f;
    """,
    dag=extractDag
)

# Load monthly flights data
load_monthly_flights = SnowflakeOperator(
    task_id='load_monthly_flights',
    snowflake_conn_id='snowflake_conn',
    sql="""
    USE WAREHOUSE COMPUTE_WH;
    USE DATABASE FINAL_PROJECT;
    USE SCHEMA PUBLIC;
    
    -- Transform and load into final table
    INSERT INTO monthly_flights (
        flight_id,
        price_raw,
        price_formatted,
        origin_id,
        destination_id,
        departure_time,
        arrival_time,
        airline_name,
        flight_number
    )
    WITH json_data AS (
        SELECT PARSE_JSON('{{ task_instance.xcom_pull(task_ids='read_monthly_json') }}') as json
    )
    SELECT DISTINCT
        r.value:id::VARCHAR as flight_id,
        r.value:content:rawPrice::FLOAT as price_raw,
        r.value:content:price::VARCHAR as price_formatted,
        r.value:content:outboundLeg:originAirport:skyCode::VARCHAR as origin_id,
        r.value:content:outboundLeg:destinationAirport:skyCode::VARCHAR as destination_id,
        r.value:content:outboundLeg:localDepartureDate::TIMESTAMP as departure_time,
        r.value:content:outboundLeg:localDepartureDate::TIMESTAMP as arrival_time,
        SPLIT_PART(r.value:id::VARCHAR, '*', 7)::VARCHAR as airline_name,
        'N/A' as flight_number
    FROM json_data,
    LATERAL FLATTEN(input => json:data:flightQuotes:results) r
    WHERE r.value:type::VARCHAR = 'FLIGHT_QUOTE';
    """,
    dag=extractDag
)

# Set task dependencies
init_database >> [create_daily_flights_table, create_monthly_flights_table]
create_daily_flights_table >> read_daily_json >> process_daily_json >> load_daily_flights
create_monthly_flights_table >> read_monthly_json >> load_monthly_flights

extractDag
