#!/usr/bin/env python
"""
CLI tool for testing the search function in chatbot_app/search_engine.py
"""
import os
import sys
import json
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

def main():
    """Main CLI function for testing the search functionality."""
    # Import after Django setup
    from chatbot_app.search_engine import search, format_search_results, get_searchable_models
    
    # Check arguments
    if len(sys.argv) < 2:
        print("\nUsage: python search_cli.py \"your search query\" [user_email]\n")
        print("Examples:")
        print("  python search_cli.py \"find cybersecurity articles\"")
        print("  python search_cli.py \"what cyber challenges are available\" test@example.com")
        print("\nAvailable searchable models:")
        
        # Display available models
        models = get_searchable_models()
        for key, model in models.items():
            print(f"  - {model.__name__}")
        
        return 1
    
    # Get query and optional user
    query = sys.argv[1]
    user = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"\n=== Testing search function ===")
    print(f"Query: \"{query}\"")
    if user:
        print(f"User: {user}")
    
    # Perform search
    try:
        results = search(query, user=user)
        print("\nRaw search results:")
        print(json.dumps(results, indent=2, default=str))
        
        # Format results for display (optional)
        print("\nFormatted for display:")
        formatted = format_search_results(results, query)
        print(json.dumps(formatted, indent=2, default=str))
        
        # Display result summary
        if isinstance(results, dict) and 'results' in results:
            total = len(results['results'])
            model_types = set()
            for result in results['results']:
                if 'model' in result:
                    model_types.add(result['model'])
            
            print(f"\nFound {total} result(s) across {len(model_types)} model type(s):")
            for model in model_types:
                count = sum(1 for r in results['results'] if r.get('model') == model)
                print(f"  - {model}: {count} result(s)")
        
    except Exception as e:
        print(f"Error during search: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 