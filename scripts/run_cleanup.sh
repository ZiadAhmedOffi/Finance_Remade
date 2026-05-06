#!/bin/bash

# 1. Update .env back to default local database
echo "Step 1: Reverting .env to default local database..."

if [ -f .env ]; then
    # Helper function to update or append keys in .env
    update_env() {
        key=$1
        val=$2
        if grep -q "^$key=" .env; then
            sed -i "s|^$key=.*|$key=$val|" .env
        else
            echo "$key=$val" >> .env
        fi
    }

    # We revert DB_NAME to the standard local name.
    # We also keep the local credentials (HOST, PORT, USER, PASS) 
    # but pointing to the main dev db.
    update_env "DB_NAME" "funds_manager_db"
else
    echo "Error: .env file not found."
    exit 1
fi

# 2. Run the cleanup script
echo "Step 2: Dropping temporary cloned database..."
source backend/backend-venv/bin/activate
python3 scripts/cleanup_db.py

if [ $? -eq 0 ]; then
    echo "--- SUCCESS ---"
    echo "Django is now back to: funds_manager_db"
else
    echo "Warning: Database cleanup script encountered an error."
    exit 1
fi
