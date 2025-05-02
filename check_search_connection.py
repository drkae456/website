#!/usr/bin/env python
"""
Command-line tool to check the search engine connection status.
Uses the Django management command we created.
"""
import os
import sys
from django.core.management import execute_from_command_line

def main():
    """
    Main entry point for the script.
    Simply runs the Django management command we created.
    """
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
    
    # Use Django's management framework to run our command
    execute_from_command_line(['manage.py', 'check_search'])

if __name__ == "__main__":
    main() 