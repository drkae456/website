#!/usr/bin/env python
"""
Test script for the format_search_results function from chatbot_app/search_engine.py.
"""
from django.test import TestCase
from django.utils import timezone
import json

class FormatSearchResultsTestCase(TestCase):
    """Test case for the format_search_results function."""
    
    def setUp(self):
        """Set up test data for formatting tests."""
        from home.models import User, APIModel, Article, CyberChallenge
        
        # Create a test user
        self.user = User.objects.create(
            email="test@example.com",
            first_name="Test",
            last_name="User"
        )
        
        # Create a test API model
        self.api_model = APIModel.objects.create(
            name="Security API",
            field_name="auth_token",
            description="An API for handling security authentication"
        )
        
        # Create a test article
        self.article = Article.objects.create(
            title="Cybersecurity Basics",
            content="<p>Learn about the basics of cybersecurity and protection</p>",
            author=self.user,
            featured=True
        )
        
        # Create a test challenge
        self.challenge = CyberChallenge.objects.create(
            title="Web Security Challenge",
            description="Test your knowledge of web security",
            question="What is XSS?",
            choices={"a": "Cross-Site Scripting", "b": "Cross-Server Sharing", "c": "Complex Security System"},
            correct_answer="a",
            explanation="XSS stands for Cross-Site Scripting, a type of vulnerability",
            difficulty="medium",
            category="web",
            points=10
        )
        
        # Create sample search results
        self.api_result = {
            "id": self.api_model.id,
            "model": "APIModel",
            "name": self.api_model.name,
            "field_name": self.api_model.field_name,
            "description": self.api_model.description
        }
        
        self.article_result = {
            "id": self.article.id,
            "model": "Article",
            "title": self.article.title,
            "content": self.article.content
        }
        
        self.challenge_result = {
            "id": self.challenge.id,
            "model": "CyberChallenge",
            "title": self.challenge.title,
            "description": self.challenge.description,
            "difficulty": self.challenge.difficulty,
            "category": self.challenge.category
        }
    
    def test_format_search_results_empty(self):
        """Test that format_search_results handles empty results properly."""
        from chatbot_app.search_engine import format_search_results
        
        # Test with empty results
        empty_results = {"results": []}
        formatted = format_search_results(empty_results, "test query")
        
        # Check structure
        self.assertIsInstance(formatted, dict)
        self.assertEqual(formatted['total'], 0)
        self.assertEqual(len(formatted['results']), 0)
        self.assertEqual(formatted['query'], "test query")
        self.assertIn('timestamp', formatted)
    
    def test_format_search_results_with_error(self):
        """Test that format_search_results handles error results properly."""
        from chatbot_app.search_engine import format_search_results
        
        # Test with error results
        error_results = {"error": "Could not understand query"}
        formatted = format_search_results(error_results, "invalid query")
        
        # Check structure
        self.assertIsInstance(formatted, dict)
        self.assertEqual(formatted['total'], 0)
        self.assertEqual(len(formatted['results']), 0)
        self.assertEqual(formatted['query'], "invalid query")
        self.assertEqual(formatted['error'], "Could not understand query")
    
    def test_format_search_results_with_api_model(self):
        """Test that format_search_results formats API model results correctly."""
        from chatbot_app.search_engine import format_search_results
        
        # Test with API model results
        api_results = {
            "results": [self.api_result]
        }
        
        formatted = format_search_results(api_results, "find security API")
        
        # Check structure
        self.assertIsInstance(formatted, dict)
        self.assertEqual(formatted['total'], 1)
        self.assertEqual(len(formatted['results']), 1)
        
        # Check first result
        result = formatted['results'][0]
        self.assertEqual(result['id'], self.api_model.id)
        self.assertEqual(result['model'], "apimodel")
        self.assertIn('title', result)
        self.assertIn('description', result)
        self.assertIn('url', result)
        
        # Check title format (should contain emoji, model label, and name)
        self.assertIn("api model", result['title'].lower())
        self.assertIn("security api", result['title'].lower())
    
    def test_format_search_results_with_challenge(self):
        """Test that format_search_results formats challenge results correctly."""
        from chatbot_app.search_engine import format_search_results
        
        # Test with challenge results
        challenge_results = {
            "results": [self.challenge_result]
        }
        
        formatted = format_search_results(challenge_results, "find security challenges")
        
        # Check structure
        self.assertIsInstance(formatted, dict)
        self.assertEqual(formatted['total'], 1)
        self.assertEqual(len(formatted['results']), 1)
        
        # Check result
        result = formatted['results'][0]
        self.assertEqual(result['id'], self.challenge.id)
        self.assertEqual(result['model'], "cyberchallenge")
        
        # Verify that difficulty is included in title for challenges
        self.assertIn("medium", result['title'].lower())
        self.assertIn("challenge", result['title'].lower())
    
    def test_format_search_results_with_mixed_models(self):
        """Test that format_search_results handles mixed model types."""
        from chatbot_app.search_engine import format_search_results
        
        # Test with mixed model results
        mixed_results = {
            "results": [self.api_result, self.article_result, self.challenge_result]
        }
        
        formatted = format_search_results(mixed_results, "find security info")
        
        # Check structure
        self.assertEqual(formatted['total'], 3)
        self.assertEqual(len(formatted['results']), 3)
        
        # Check that we have all three model types
        model_types = {result['model'] for result in formatted['results']}
        self.assertEqual(len(model_types), 3)
        self.assertIn('apimodel', model_types)
        self.assertIn('article', model_types)
        self.assertIn('cyberchallenge', model_types)
        
        # Verify URLs are formatted correctly for each model
        for result in formatted['results']:
            if result['model'] == 'apimodel':
                self.assertIn('/api_models/', result['url'])
            elif result['model'] == 'article':
                self.assertIn('/articles/', result['url'])
            elif result['model'] == 'cyberchallenge':
                self.assertIn('/cyber_challenges/', result['url'])
    
    def test_format_search_results_with_long_description(self):
        """Test that format_search_results truncates long descriptions."""
        from chatbot_app.search_engine import format_search_results
        
        # Create a result with a very long description
        long_desc_result = {
            "id": 999,
            "model": "Article",
            "title": "Long Description Article",
            "content": "This is a very long description that should be truncated. " * 10
        }
        
        results = {
            "results": [long_desc_result]
        }
        
        formatted = format_search_results(results, "long article")
        
        # Check that description is truncated
        result = formatted['results'][0]
        self.assertLess(len(result['description']), 201)
        self.assertTrue(result['description'].endswith('...'))

if __name__ == "__main__":
    # Run the test using Django's test framework
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'test', 'test_format_search_results.FormatSearchResultsTestCase', '-v', '2']) 