#!/usr/bin/env python
"""
Command-line interface for testing the search_engine function.
"""
import os
import sys
import django
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

# Now import the necessary modules
from chatbot_app.search_engine import search_engine, identify_model_from_prompt, get_searchable_models

def display_results(result):
    """Display search results in a readable format."""
    if not result:
        print("No results returned.")
        return
    
    if isinstance(result, dict):
        # Check for error response
        if 'error' in result:
            print(f"\nError: {result['error']}")
            return
        
        # Check if it's the standard response format
        if 'results' in result:
            print(f"\nFound {result['total']} results:")
            print("-" * 50)
            
            # Print metadata if available
            if 'query_info' in result:
                query_info = result['query_info']
                print("\nQuery Information:")
                for key, value in query_info.items():
                    if key != 'timestamp':  # Skip timestamp for cleaner output
                        print(f"  {key}: {value}")
            
            # Print results
            if result['results']:
                print("\nResults:")
                for i, item in enumerate(result['results'], 1):
                    print(f"\nResult {i}:")
                    for key, value in item.items():
                        # Truncate long values
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:97] + "..."
                        print(f"  {key}: {value}")
            else:
                print("\nNo matching results found.")
        else:
            # Unknown format, print as JSON
            print("\nResult:")
            print(json.dumps(result, indent=2))
    else:
        print(f"\nUnexpected result type: {type(result)}")
        print(result)

def test_model_identification():
    """Test the model identification functionality."""
    models = get_searchable_models()
    
    print("\n=== Model Identification Test ===")
    print("This will show which models are detected from your queries.")
    
    while True:
        query = input("\nEnter a query to identify the model (or 'q' to quit): ")
        if query.lower() == 'q':
            break
        
        model_key = identify_model_from_prompt(query, models)
        if model_key:
            model_class = models[model_key]
            print(f"Identified model: {model_key} ({model_class.__name__})")
        else:
            print("No model could be identified from your query.")

def main():
    """Main CLI function."""
    print("\n=== Search Engine CLI ===")
    print("This tool lets you test the search_engine function interactively.")
    
    while True:
        print("\n" + "=" * 50)
        print("Options:")
        print("1. Search with a query")
        print("2. Test model identification")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == '1':
            query = input("\nEnter your search query: ")
            print(f"\nSearching for: '{query}'...")
            try:
                result = search_engine(query)
                display_results(result)
            except Exception as e:
                print(f"\nError: {str(e)}")
        
        elif choice == '2':
            test_model_identification()
        
        elif choice == '3':
            break
        
        else:
            print("\nInvalid choice. Please try again.")
    
    print("\nThank you for using Search Engine CLI!")

if __name__ == "__main__":
    main() 