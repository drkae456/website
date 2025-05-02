#!/usr/bin/env python
from django.test import TestCase
from django.core.management import call_command
import sys

class SearchModelTestCase(TestCase):
    """Test case for the search_model function."""
    
    def setUp(self):
        """Set up test data."""
        # Load test data from fixtures if available
        try:
            call_command('loaddata', 'test_data.json', verbosity=0)
        except:
            print("Note: test_data fixture not found, using empty database")
    
    def test_search_model(self):
        """Test the search_model function with different models and search terms."""
        from chatbot_app.search_engine import search_model
        from home.models import APIModel, CyberChallenge, Announcement, Article, BlogPost
        
        print("\n=== Testing search_model function ===\n")
        
        # Test case 1: Search APIModel with an empty term
        print("Test case 1: Search APIModel with an empty term")
        results = search_model(APIModel)
        print(f"Results count: {len(results)}")
        for result in results[:3]:  # Show up to 3 results
            if hasattr(result, 'name') and hasattr(result, 'description'):
                print(f"- {result.name}: {result.description[:50]}...")
        
        # Test case 2: Search CyberChallenge with a specific term
        print("\nTest case 2: Search CyberChallenge with term 'security'")
        results = search_model(CyberChallenge, term='security')
        print(f"Results count: {len(results)}")
        for result in results[:3]:  # Show up to 3 results
            if hasattr(result, 'title') and hasattr(result, 'description'):
                print(f"- {result.title}: {result.description[:50]}...")
        
        # Test case 3: Search Announcement with today's date
        print("\nTest case 3: Search Announcement with term 'today'")
        results = search_model(Announcement, term='today')
        print(f"Results count: {len(results)}")
        for result in results[:3]:
            if hasattr(result, 'message'):
                print(f"- Message: {result.message[:50]}...")
        
        # Test case 4: Search Article with a specific term and limit
        print("\nTest case 4: Search Article with term 'cyber' and limit=5")
        results = search_model(Article, term='cyber', limit=5)
        print(f"Results count: {len(results)}")
        for result in results[:5]:
            if hasattr(result, 'title') and hasattr(result, 'content'):
                print(f"- {result.title}: {result.content[:50]}...")
        
        # Test case 5: Search BlogPost with a specific term
        print("\nTest case 5: Search BlogPost with term 'security'")
        results = search_model(BlogPost, term='security')
        print(f"Results count: {len(results)}")
        for result in results[:3]:
            if hasattr(result, 'title') and hasattr(result, 'body'):
                print(f"- {result.title}: {result.body[:50]}...")

if __name__ == "__main__":
    # Run the test case
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'test', 'test_search_model.SearchModelTestCase']) 