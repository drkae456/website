#!/usr/bin/env python
"""
Test script for the format_model_response function.
"""
from django.test import TestCase
from django.utils import timezone

class FormatModelResponseTestCase(TestCase):
    """Test case for the format_model_response function."""
    
    def setUp(self):
        """Set up test data for formatting tests."""
        from home.models import User, APIModel, Article
        
        # Create a test user
        self.user = User.objects.create(
            email="test@example.com",
            first_name="Test",
            last_name="User"
        )
        
        # Create some test model instances
        self.api_model1 = APIModel.objects.create(
            name="Test API",
            field_name="api_field",
            description="Test API description"
        )
        
        self.api_model2 = APIModel.objects.create(
            name="Another API",
            field_name="another_field",
            description="Another API description"
        )
        
        self.article = Article.objects.create(
            title="Test Article",
            content="<p>Test article content</p>",
            author=self.user,
            featured=True
        )
    
    def test_format_model_response_empty(self):
        """Test that format_model_response handles empty results properly."""
        from chatbot_app.search_engine import format_model_response
        
        # Test with empty results
        formatted = format_model_response([])
        
        # Check structure
        self.assertIsInstance(formatted, dict)
        self.assertEqual(formatted['total'], 0)
        self.assertEqual(len(formatted['results']), 0)
        self.assertIn('query_info', formatted)
    
    def test_format_model_response_with_results(self):
        """Test that format_model_response formats model results correctly."""
        from chatbot_app.search_engine import format_model_response
        
        # Test with APIModel results
        results = [self.api_model1, self.api_model2]
        query_info = {'identified_model': 'apimodel', 'search_term': 'test'}
        
        formatted = format_model_response(results, query_info)
        
        # Check structure
        self.assertIsInstance(formatted, dict)
        self.assertEqual(formatted['total'], 2)
        self.assertEqual(len(formatted['results']), 2)
        self.assertEqual(formatted['query_info'], query_info)
        
        # Check first result
        first_result = formatted['results'][0]
        self.assertEqual(first_result['id'], self.api_model1.id)
        self.assertEqual(first_result['model'], 'APIModel')
        self.assertIn('name', first_result)
        self.assertIn('description', first_result)
        
    def test_format_model_response_mixed_models(self):
        """Test that format_model_response handles mixed model types."""
        from chatbot_app.search_engine import format_model_response
        
        # Test with mixed model results
        results = [self.api_model1, self.article]
        
        formatted = format_model_response(results)
        
        # Check structure
        self.assertEqual(formatted['total'], 2)
        self.assertEqual(len(formatted['results']), 2)
        
        # Check result types
        models = [result['model'] for result in formatted['results']]
        self.assertIn('APIModel', models)
        self.assertIn('Article', models)
        
        # Check article fields
        article_result = next(r for r in formatted['results'] if r['model'] == 'Article')
        self.assertEqual(article_result['id'], self.article.id)
        self.assertIn('title', article_result)
        self.assertIn('content', article_result)

if __name__ == "__main__":
    # Run the test using Django's test framework
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'test', 'test_format_model_response.FormatModelResponseTestCase', '-v', '2']) 