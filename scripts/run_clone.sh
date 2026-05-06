#!/bin/bash

# Load temporary database name and local credentials from .env
if [ -f .env ]; then
    TEMP_DB=$(grep "^TEMP_DB_NAME=" .env | cut -d '=' -f2)
    L_HOST=$(grep "^LOCAL_DB_HOST=" .env | cut -d '=' -f2)
    L_PORT=$(grep "^LOCAL_DB_PORT=" .env | cut -d '=' -f2)
    L_USER=$(grep "^LOCAL_DB_USER=" .env | cut -d '=' -f2)
    L_PASS=$(grep "^LOCAL_DB_PASSWORD=" .env | cut -d '=' -f2)
else
    echo "Error: .env file not found."
    exit 1
fi

# 1. Run the clone script
echo "Step 1: Cloning remote database..."
source backend/backend-venv/bin/activate
python3 scripts/clone_db.py

if [ $? -eq 0 ]; then
    echo "Step 2: Updating .env to use the cloned database..."
    
    # Helper function to update or append keys in .env
    update_env() {
        key=$1
        val=$2
        if grep -q "^$key=" .env; then
            # Using | as delimiter in sed to handle potential special chars in values
            sed -i "s|^$key=.*|$key=$val|" .env
        else
            echo "$key=$val" >> .env
        fi
    }

    update_env "DB_NAME" "$TEMP_DB"
    update_env "DB_HOST" "$L_HOST"
    update_env "DB_PORT" "$L_PORT"
    update_env "DB_USER" "$L_USER"
    update_env "DB_PASSWORD" "$L_PASS"

    echo "--- SUCCESS ---"
    echo "Django is now configured to use: $TEMP_DB"
else
    echo "Error: Database cloning failed. .env was not modified."
    exit 1
fi
