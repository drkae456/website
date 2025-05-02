"""
Test suite for both search engine implementations (original and v2).
"""
from django.test import TestCase
from django.utils import timezone
from chatbot_app.search_engine import format_search_results as format_search_results_v1
from chatbot_app.search_engine_v2 import format_search_results as format_search_results_v2
from home.models import User, CyberChallenge, Article, APIModel

class SearchEngineFormattingTestCase(TestCase):
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create(
            email="test@example.com",
            first_name="Test",
            last_name="User"
        )
        
        # Create test challenge with all required fields
        self.challenge = CyberChallenge.objects.create(
            title="XSS Challenge",
            description="Test your XSS knowledge",
            question="What is XSS?",
            choices={"a": "Cross-Site Scripting", "b": "Cross-Server Sharing", "c": "Complex Security System"},
            correct_answer="a",
            explanation="XSS stands for Cross-Site Scripting, a type of vulnerability",
            difficulty="hard",
            category="web",
            points=100
        )
        
        # Create test article
        self.article = Article.objects.create(
            title="Security Best Practices",
            content="Learn about security",
            author=self.user
        )
        
        # Create test API model
        self.api = APIModel.objects.create(
            name="Auth API",
            description="Authentication API",
            field_name="token"
        )
        
        # Prepare test data
        self.challenge_data = {
            "results": [{
                "id": self.challenge.id,
                "model": "CyberChallenge",
                "title": self.challenge.title,
                "description": self.challenge.description,
                "difficulty": self.challenge.difficulty,
                "category": self.challenge.category,
                "question": self.challenge.question,
                "choices": self.challenge.choices,
                "correct_answer": self.challenge.correct_answer,
                "explanation": self.challenge.explanation
            }]
        }
        
        self.mixed_data = {
            "results": [
                {
                    "id": self.challenge.id,
                    "model": "CyberChallenge",
                    "title": self.challenge.title,
                    "description": self.challenge.description,
                    "difficulty": self.challenge.difficulty,
                    "category": self.challenge.category,
                    "question": self.challenge.question,
                    "choices": self.challenge.choices,
                    "correct_answer": self.challenge.correct_answer,
                    "explanation": self.challenge.explanation
                },
                {
                    "id": self.article.id,
                    "model": "Article",
                    "title": self.article.title,
                    "content": self.article.content
                },
                {
                    "id": self.api.id,
                    "model": "APIModel",
                    "name": self.api.name,
                    "description": self.api.description
                }
            ]
        }

    def test_v1_challenge_formatting(self):
        """Test that v1 includes difficulty in challenge titles."""
        formatted = format_search_results_v1(self.challenge_data, "find challenges")
        result = formatted['results'][0]
        self.assertIn(self.challenge.difficulty, result['title'].lower())
        self.assertEqual(result['model'], 'cyberchallenge')

    def test_v2_challenge_formatting(self):
        """Test that v2 includes difficulty in challenge titles."""
        formatted = format_search_results_v2(self.challenge_data, "find challenges")
        result = formatted['results'][0]
        self.assertIn(self.challenge.difficulty, result['title'].lower())
        self.assertEqual(result['model'], 'cyberchallenge')

    def test_v1_mixed_results(self):
        """Test v1 formatting with mixed model types."""
        formatted = format_search_results_v1(self.mixed_data, "find all")
        self.assertEqual(len(formatted['results']), 3)
        models = {r['model'] for r in formatted['results']}
        self.assertEqual(models, {'cyberchallenge', 'article', 'apimodel'})

    def test_v2_mixed_results(self):
        """Test v2 formatting with mixed model types."""
        formatted = format_search_results_v2(self.mixed_data, "find all")
        self.assertEqual(len(formatted['results']), 3)
        models = {r['model'] for r in formatted['results']}
        self.assertEqual(models, {'cyberchallenge', 'article', 'apimodel'})

    def test_v1_error_handling(self):
        """Test v1 error case handling."""
        error_data = {"error": "Not found"}
        formatted = format_search_results_v1(error_data, "invalid query")
        self.assertIn('error', formatted)
        self.assertEqual(formatted['total'], 0)

    def test_v2_error_handling(self):
        """Test v2 error case handling."""
        error_data = {"error": "Not found"}
        formatted = format_search_results_v2(error_data, "invalid query")
        self.assertIn('error', formatted)
        self.assertEqual(formatted['total'], 0)

    def test_v1_empty_results(self):
        """Test v1 with empty results."""
        empty_data = {"results": []}
        formatted = format_search_results_v1(empty_data, "no results")
        self.assertEqual(formatted['total'], 0)
        self.assertEqual(len(formatted['results']), 0)

    def test_v2_empty_results(self):
        """Test v2 with empty results."""
        empty_data = {"results": []}
        formatted = format_search_results_v2(empty_data, "no results")
        self.assertEqual(formatted['total'], 0)
        self.assertEqual(len(formatted['results']), 0)

    def test_description_truncation(self):
        """Test that long descriptions are properly truncated."""
        long_desc = "x" * 300
        data = {
            "results": [{
                "id": 1,
                "model": "Article",
                "title": "Long Article",
                "content": long_desc
            }]
        }
        
        # Test v1
        formatted_v1 = format_search_results_v1(data, "long article")
        self.assertTrue(formatted_v1['results'][0]['description'].endswith('...'))
        self.assertLess(len(formatted_v1['results'][0]['description']), 201)
        
        # Test v2
        formatted_v2 = format_search_results_v2(data, "long article")
        self.assertTrue(formatted_v2['results'][0]['description'].endswith('...'))
        self.assertLess(len(formatted_v2['results'][0]['description']), 201) 