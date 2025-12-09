#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create credentials.json from Environment Variable
# (We will set GOOGLE_CREDENTIALS_JSON in the dashboard later)
if [ -n "$GOOGLE_CREDENTIALS_JSON" ]; then
    echo "$GOOGLE_CREDENTIALS_JSON" > credentials.json
fi

# Collect static files
python manage.py collectstatic --noinput

# Apply database migrations
python manage.py migrate