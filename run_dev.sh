#!/bin/bash

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check if .env file exists, if not create it
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOL
# True for development, False for production
DEBUG=True

# Database Configuration
DB_ENGINE=postgresql
DB_HOST=localhost
DB_NAME=website_db
DB_USERNAME=postgres
DB_PASS=postgres
DB_PORT=5432

# Django Secret Key
SECRET_KEY=django-insecure-your-secret-key-here
EOL
    echo ".env file created"
fi

# Start PostgreSQL
echo "Starting PostgreSQL..."
brew services restart postgresql@15

# Wait for PostgreSQL to start
sleep 2

# Create PostgreSQL user if it doesn't exist
echo "Creating PostgreSQL user..."
createuser -s postgres 2>/dev/null || true

# Create database if it doesn't exist
echo "Creating database if it doesn't exist..."
createdb website_db 2>/dev/null || true

# Set password for postgres user
echo "Setting password for postgres user..."
psql -c "ALTER USER postgres WITH PASSWORD 'postgres';" postgres 2>/dev/null || true

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser if it doesn't exist..."
python3 manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@example.com').exists():
    User.objects.create_superuser('admin@example.com', 'admin12345')
EOF

# Start development server
echo "Starting development server..."
python manage.py runserver