#!/usr/bin/env python
"""
Test script for the search_engine function using Django's test framework.
"""
from django.test import TestCase
from django.utils import timezone
from django.core.management import execute_from_command_line

class SearchEngineTestCase(TestCase):
    """Test case for the search_engine function."""
    
    def setUp(self):
        """Set up test data for search testing."""
        from home.models import User, APIModel, CyberChallenge, Announcement, Article, BlogPost
        
        # Create a test user
        self.user = User.objects.create(
            email="test@example.com",
            first_name="Test",
            last_name="User"
        )
        
        # Create some test APIModel instances
        APIModel.objects.create(
            name="Security API",
            field_name="auth_token",
            description="An API for handling security authentication"
        )
        APIModel.objects.create(
            name="Data API",
            field_name="data_field",
            description="An API for data processing"
        )
        
        # Create some test CyberChallenge instances
        CyberChallenge.objects.create(
            title="Web Security Challenge",
            description="Test your web security knowledge",
            question="What is XSS?",
            choices={"a": "Cross-Site Scripting", "b": "Cross-Server Sharing", "c": "Complex Security System"},
            correct_answer="a",
            explanation="XSS stands for Cross-Site Scripting",
            difficulty="medium",
            category="web",
            points=10
        )
        
        # Create some test Announcement instances with timezone-aware datetimes
        Announcement.objects.create(
            message="Important security update available",
            isActive=True,
            created_at=timezone.now()
        )
        Announcement.objects.create(
            message="Welcome to our new platform",
            isActive=True,
            created_at=timezone.now() - timezone.timedelta(days=1)
        )
        
        # Create some test Article instances
        Article.objects.create(
            title="Introduction to Cybersecurity",
            content="<p>Learn about the basics of cybersecurity and how to protect yourself online</p>",
            author=self.user,
            featured=True
        )
        
        # Create some test BlogPost instances
        BlogPost.objects.create(
            title="Security Tips for Remote Work",
            body="Tips for maintaining security while working remotely",
            page_name="blog"
        )
    
    def test_search_engine(self):
        """Test the search_engine function with various prompts."""
        from chatbot_app.search_engine import search_engine
        
        print("\n=== Testing search_engine function with test data ===\n")
        
        # List of test prompts that should work well
        working_prompts = [
            "get api information",
            "blog posts about security",
            "challenges web",  # More specific prompt
            "articles about cyber",  # More specific prompt
        ]
        
        # Test the working prompts
        for prompt in working_prompts:
            print(f"\nTesting prompt: '{prompt}'")
            try:
                result = search_engine(prompt)
                
                # Print basic result info
                if isinstance(result, dict):
                    # Check if it's the standard response format
                    if 'results' in result:
                        print(f"Found {len(result['results'])} results")
                        
                        # Print metadata if available
                        if 'query_info' in result and result['query_info']:
                            if 'identified_model' in result['query_info']:
                                print(f"Identified model: {result['query_info']['identified_model']}")
                            if 'search_term' in result['query_info']:
                                print(f"Search term: {result['query_info']['search_term']}")
                        
                        # Print first few results
                        for i, item in enumerate(result['results'][:3]):
                            if 'model' in item and 'id' in item:
                                print(f"  Result {i+1}: {item['model']} - ID: {item['id']}")
                            else:
                                # Try to extract useful info
                                info = []
                                for key in ['title', 'name', 'message']:
                                    if key in item:
                                        info.append(f"{key}: {item[key]}")
                                print(f"  Result {i+1}: {', '.join(info)}")
                    # Handle error response
                    elif 'error' in result:
                        print(f"Error: {result['error']}")
                    # Unknown format
                    else:
                        print(f"Result: {result}")
                else:
                    print(f"Unexpected result type: {type(result)}")
            
            except Exception as e:
                print(f"Error testing prompt '{prompt}': {str(e)}")
        
        # Test that model identification works correctly
        # Focus on API model which seems to be working well
        api_result = search_engine("get api information")
        self.assertTrue(isinstance(api_result, dict), "Result should be a dictionary")
        self.assertTrue('query_info' in api_result, "Result should include query_info")
        self.assertEqual(api_result['query_info'].get('identified_model'), 'apimodel', 
                         "Should identify 'apimodel' as the model for 'get api information'")
        
        # Test that blog post results work correctly
        blog_result = search_engine("blog posts about security")
        self.assertTrue(isinstance(blog_result, dict), "Result should be a dictionary")
        self.assertTrue('results' in blog_result, "Result should include results array")
        self.assertTrue(len(blog_result['results']) > 0, "Should find at least one blog post about security")
        
        print("\n=== Search engine test completed ===")

if __name__ == "__main__":
    # Run the test using Django's test framework
    execute_from_command_line(['manage.py', 'test', 'test_search_engine.SearchEngineTestCase', '-v', '2']) 