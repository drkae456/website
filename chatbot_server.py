#!/usr/bin/env python
"""Script to run the chatbot service on a separate port."""
import os
import sys

def main():
    """Run the chatbot service."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Override system arguments to run the chatbot service on port 5005
    # Original sys.argv will be something like ['chatbot_server.py']
    # We transform it to ['chatbot_server.py', 'runserver', '0.0.0.0:5005']
    chatbot_port = os.environ.get('CHATBOT_PORT', '5005')
    sys.argv = [sys.argv[0], 'runserver', f'0.0.0.0:{chatbot_port}']
    
    print(f"Starting chatbot service on port {chatbot_port}...")
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main() 