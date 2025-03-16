#!/bin/bash

# Install dependencies
echo "Building the project.."
python3.9 -m pip install -r requirements.txt

# Run migrations (if any)
echo "Make Migration..."
python3.9 manage.py migrate

# Collect static files (for deployment)
python3.9 manage.py collectstatic --noinput --clear