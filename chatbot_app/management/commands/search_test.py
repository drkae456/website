"""
Django management command to test the search function.
"""
import json
from django.core.management.base import BaseCommand
from chatbot_app.search_engine import search, format_search_results, get_searchable_models

class Command(BaseCommand):
    help = 'Tests the search function with a provided query'

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            'query',
            type=str,
            help='The search query to test',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Optional user identifier (e.g., email)',
            default=None,
        )
        parser.add_argument(
            '--formatted',
            action='store_true',
            help='Show formatted results for display',
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        query = options['query']
        user = options.get('user')
        show_formatted = options.get('formatted', False)
        
        self.stdout.write(self.style.SUCCESS("\n=== Testing search function ===\n"))
        self.stdout.write(f"Query: \"{query}\"")
        if user:
            self.stdout.write(f"User: {user}")
        
        try:
            # Perform the search
            results = search(query, user=user)
            
            # Display raw results
            self.stdout.write("\nRaw search results:")
            self.stdout.write(json.dumps(results, indent=2, default=str))
            
            # Display formatted results if requested
            if show_formatted:
                self.stdout.write("\nFormatted for display:")
                formatted = format_search_results(results, query)
                self.stdout.write(json.dumps(formatted, indent=2, default=str))
            
            # Display result summary
            if isinstance(results, dict) and 'results' in results:
                total = len(results['results'])
                model_types = set()
                for result in results['results']:
                    if 'model' in result:
                        model_types.add(result['model'])
                
                self.stdout.write(f"\nFound {total} result(s) across {len(model_types)} model type(s):")
                for model in model_types:
                    count = sum(1 for r in results['results'] if r.get('model') == model)
                    self.stdout.write(f"  - {model}: {count} result(s)")
            
            # If no results or error, show available models
            if not results.get('results') or 'error' in results:
                self.stdout.write("\nAvailable searchable models:")
                models = get_searchable_models()
                for key, model in models.items():
                    self.stdout.write(f"  - {model.__name__}")
                
                # Show format of the search function
                self.stdout.write("\nUsage examples:")
                self.stdout.write("  python manage.py search_test \"find cybersecurity articles\"")
                self.stdout.write("  python manage.py search_test \"what cyber challenges are available\" --user=test@example.com")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during search: {str(e)}"))
            import traceback
            traceback.print_exc() 