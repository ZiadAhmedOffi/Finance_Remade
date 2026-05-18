import os
import subprocess
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

def run_command(command, env=None):
    try:
        process = subprocess.Popen(
            command,
            env=env,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            print(f"Command failed with return code {process.returncode}")
            print(f"Stderr: {stderr}")
            return False
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def clone_database():
    # Configuration
    online_host = get_env_var("ONLINE_DB_HOST")
    online_name = get_env_var("ONLINE_DB_NAME")
    online_user = get_env_var("ONLINE_DB_USER")
    online_pass = get_env_var("ONLINE_DB_PASSWORD")

    local_host = get_env_var("LOCAL_DB_HOST")
    local_port = get_env_var("LOCAL_DB_PORT")
    local_user = get_env_var("LOCAL_DB_USER")
    local_pass = get_env_var("LOCAL_DB_PASSWORD", required=False)
    temp_db_name = get_env_var("TEMP_DB_NAME")

    print(f"--- Starting Database Cloning to {temp_db_name} ---")

    # 1. Recreate the temporary database
    try:
        print(f"Dropping and recreating local database: {temp_db_name}")
        conn = psycopg2.connect(
            host=local_host,
            port=local_port,
            user=local_user,
            password=local_pass,
            database="postgres" # Connect to default db to manage others
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Terminate existing connections to the temp db if any
        cur.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{temp_db_name}'
              AND pid <> pg_backend_pid();
        """)
        
        cur.execute(f"DROP DATABASE IF EXISTS {temp_db_name};")
        cur.execute(f"CREATE DATABASE {temp_db_name};")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Failed to recreate local database: {e}")
        sys.exit(1)

    # 2. Perform the clone using pg_dump | psql
    print("Streaming data from remote to local (this may take a few minutes)...")
    
    # Supabase nuances: --schema=public, --no-owner, --no-privileges
    dump_cmd = (
        f"pg_dump -h {online_host} -U {online_user} -d {online_name} "
        f"--schema=public --no-owner --no-privileges"
    )
    
    restore_cmd = (
        f"psql -h {local_host} -p {local_port} -U {local_user} -d {temp_db_name}"
    )
    
    # Set passwords in environment for pg_dump and psql
    # We use env vars inside the shell command string
    full_cmd = f"PGPASSWORD='{online_pass}' {dump_cmd} | PGPASSWORD='{local_pass}' {restore_cmd}"
    
    if run_command(full_cmd):
        print(f"Successfully cloned database to {temp_db_name}")
    else:
        print("Database cloning failed.")
        sys.exit(1)

if __name__ == "__main__":
    clone_database()
