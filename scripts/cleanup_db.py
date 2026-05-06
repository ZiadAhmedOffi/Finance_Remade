import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import sys

# Load environment variables from .env
load_dotenv()

def get_env_var(name, required=True):
    val = os.getenv(name)
    if required and val is None:
        print(f"Error: Environment variable {name} not found.")
        sys.exit(1)
    if required and not val and name != "LOCAL_DB_PASSWORD":
        print(f"Error: Environment variable {name} is empty.")
        sys.exit(1)
    return val or ""

def cleanup_database():
    # Configuration
    local_host = get_env_var("LOCAL_DB_HOST")
    local_port = get_env_var("LOCAL_DB_PORT")
    local_user = get_env_var("LOCAL_DB_USER")
    local_pass = get_env_var("LOCAL_DB_PASSWORD", required=False)
    temp_db_name = get_env_var("TEMP_DB_NAME")

    print(f"--- Starting Database Cleanup for {temp_db_name} ---")

    try:
        conn = psycopg2.connect(
            host=local_host,
            port=local_port,
            user=local_user,
            password=local_pass,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # 1. Terminate existing connections to the temp db
        print(f"Terminating connections to {temp_db_name}...")
        cur.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{temp_db_name}'
              AND pid <> pg_backend_pid();
        """)
        
        # 2. Drop the database
        print(f"Dropping database {temp_db_name}...")
        cur.execute(f"DROP DATABASE IF EXISTS {temp_db_name};")
        
        cur.close()
        conn.close()
        print(f"Successfully cleaned up {temp_db_name}")
    except Exception as e:
        print(f"Cleanup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    cleanup_database()
