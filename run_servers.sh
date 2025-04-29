#!/bin/bash

# Run both the main app and the chatbot server

# Start chatbot server in the background
echo "Starting chatbot server on port 5005..."
python chatbot_server.py &
CHATBOT_PID=$!

# Start main application
echo "Starting main application on default port (8000)..."
python manage.py runserver

# When the main app is terminated, also kill the chatbot server
kill $CHATBOT_PID 