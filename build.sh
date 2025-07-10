#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create logs directory if it doesn't exist
mkdir -p logs

# Create media directories if they don't exist
mkdir -p media/recordings
mkdir -p media/responses

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py makemigrations exam
python manage.py migrate
python manage.py populate_exam_data

# Create superuser if it doesn't exist (optional for production)
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created')
else:
    print('Superuser already exists')
"

echo "Build completed successfully!"
