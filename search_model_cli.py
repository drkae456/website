#!/usr/bin/env python
"""
Command-line interface for testing the search_model function.
"""
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

# Now import the necessary modules
from chatbot_app.search_engine import search_model, get_searchable_models
from home.models import APIModel, CyberChallenge, Announcement, Article, BlogPost

def list_models():
    """List available models that can be searched."""
    print("\nAvailable models:")
    print("-" * 50)
    
    # Get models from the get_searchable_models function
    models = get_searchable_models('home')
    for i, (key, model) in enumerate(models.items(), 1):
        print(f"{i}. {model.__name__}")
    
    # Also list specific known models
    print("\nCommonly used models:")
    print("-" * 50)
    specific_models = [
        APIModel,
        CyberChallenge,
        Announcement,
        Article,
        BlogPost
    ]
    
    for i, model in enumerate(specific_models, 1):
        print(f"{i}. {model.__name__}")
    
    return specific_models

def display_results(results, limit=5):
    """Display search results in a readable format."""
    if not results:
        print("No results found.")
        return
    
    print(f"\nFound {len(results)} results:")
    print("-" * 50)
    
    # Get the first result to determine available fields
    sample = results[0]
    
    # Try to find name/title field
    title_field = None
    for field in ['title', 'name', 'subject', 'message']:
        if hasattr(sample, field):
            title_field = field
            break
    
    # Try to find content/description field
    content_field = None
    for field in ['content', 'description', 'body', 'message', 'explanation']:
        if hasattr(sample, field) and field != title_field:
            content_field = field
            break
    
    # Display results
    for i, result in enumerate(results[:limit], 1):
        print(f"\nResult {i}:")
        print(f"  ID: {result.id}")
        
        if title_field:
            title = getattr(result, title_field)
            print(f"  {title_field.capitalize()}: {title}")
        
        if content_field:
            content = getattr(result, content_field)
            # Truncate content if too long
            if len(str(content)) > 100:
                content = str(content)[:97] + "..."
            print(f"  {content_field.capitalize()}: {content}")
        
        # Print other important fields
        for field in dir(result):
            # Skip private attributes, methods, and already displayed fields
            if (field.startswith('_') or callable(getattr(result, field)) or
                field in [title_field, content_field, 'id'] or 
                field in ['DoesNotExist', 'MultipleObjectsReturned']):
                continue
            
            value = getattr(result, field)
            # Skip complex objects
            if not isinstance(value, (str, int, float, bool)) and value is not None:
                continue
                
            print(f"  {field.capitalize()}: {value}")
    
    if len(results) > limit:
        print(f"\n... and {len(results) - limit} more results.")

def main():
    """Main CLI function."""
    print("\n=== Search Model CLI ===")
    print("This tool lets you test the search_model function interactively.")
    
    # List available models
    specific_models = list_models()
    
    while True:
        print("\n" + "=" * 50)
        choice = input("\nEnter model number to search (or 'q' to quit): ")
        
        if choice.lower() == 'q':
            break
        
        try:
            model_index = int(choice) - 1
            if 0 <= model_index < len(specific_models):
                model = specific_models[model_index]
            else:
                print("Invalid model number. Please try again.")
                continue
        except ValueError:
            print("Please enter a valid number or 'q' to quit.")
            continue
        
        # Get search term
        term = input(f"\nEnter search term for {model.__name__} (leave empty for all): ")
        
        # Get result limit
        try:
            limit_input = input("\nEnter result limit (default: 5): ")
            limit = int(limit_input) if limit_input.strip() else 5
        except ValueError:
            limit = 5
            print("Using default limit of 5.")
        
        # Perform search
        print(f"\nSearching {model.__name__} for '{term}'...")
        results = search_model(model, term=term, limit=limit)
        
        # Display results
        display_results(results, limit)
    
    print("\nThank you for using Search Model CLI!")

if __name__ == "__main__":
    main() 