from airflow import settings
from airflow.models import Connection
import os

# Get environment variables
snowflake_account = os.getenv('SNOWFLAKE_ACCOUNT')
snowflake_user = os.getenv('SNOWFLAKE_USER')
snowflake_password = os.getenv('SNOWFLAKE_PASSWORD')
snowflake_warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')
snowflake_database = os.getenv('SNOWFLAKE_DATABASE')
snowflake_role = os.getenv('SNOWFLAKE_ROLE')
snowflake_schema = os.getenv('SNOWFLAKE_SCHEMA_DBT')

# Create Snowflake connection
snowflake_conn = Connection(
    conn_id='snowflake_conn',
    conn_type='snowflake',
    host=f'{snowflake_account}.snowflakecomputing.com',
    login=snowflake_user,
    password=snowflake_password,
    schema=snowflake_schema,
    extra=(
        f'{{"account": "{snowflake_account}", '
        f'"warehouse": "{snowflake_warehouse}", '
        f'"database": "{snowflake_database}", '
        f'"role": "{snowflake_role}"}}'
    )
)

# Save connection
session = settings.Session()

# Check if connection already exists
existing_conn = session.query(Connection).filter(Connection.conn_id == 'snowflake_conn').first()
if existing_conn:
    # Update existing connection
    existing_conn.conn_type = snowflake_conn.conn_type
    existing_conn.host = snowflake_conn.host
    existing_conn.login = snowflake_conn.login
    existing_conn.password = snowflake_conn.password
    existing_conn.schema = snowflake_conn.schema
    existing_conn.extra = snowflake_conn.extra
else:
    # Add new connection
    session.add(snowflake_conn)

session.commit() 