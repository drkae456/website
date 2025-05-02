#!/usr/bin/env python
from django.test import TestCase
from django.utils import timezone
from chatbot_app.search_engine import search_model
from home.models import APIModel, CyberChallenge, Announcement, Article, BlogPost, User

class SearchModelWithDataTestCase(TestCase):
    """Test case for the search_model function with actual test data."""
    
    def setUp(self):
        """Set up test data."""
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
        APIModel.objects.create(
            name="User API",
            field_name="user_field",
            description="An API for user management"
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
        CyberChallenge.objects.create(
            title="Network Security Challenge",
            description="Test your network security knowledge",
            question="What is a firewall?",
            choices={"a": "A physical wall", "b": "Security software/hardware", "c": "A type of virus"},
            correct_answer="b",
            explanation="A firewall is security software/hardware",
            difficulty="easy",
            category="network",
            points=5
        )
        
        # Create some test Announcement instances
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
        
        # Create some test Article instances - Update to include cybersecurity in content
        Article.objects.create(
            title="Introduction to Cybersecurity",
            content="<p>Learn about the basics of cybersecurity and how to protect yourself online</p>",
            author=self.user,
            featured=True
        )
        Article.objects.create(
            title="Data Protection Best Practices",
            content="<p>Best practices for protecting your data from cyber threats and hackers</p>",
            author=self.user,
            featured=False
        )
        
        # Create some test BlogPost instances
        BlogPost.objects.create(
            title="Security Tips for Remote Work",
            body="Tips for maintaining security while working remotely",
            page_name="blog"
        )
        BlogPost.objects.create(
            title="The Future of AI",
            body="Exploring the future of artificial intelligence",
            page_name="blog"
        )
    
    def test_search_model(self):
        """Test the search_model function with different models and search terms."""
        print("\n=== Testing search_model function with test data ===\n")
        
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
        results = search_model(Article, term='cyber')
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
        
        # Assert that we got the expected results
        self.assertTrue(len(search_model(APIModel, term='security')) > 0, 
                        "Should find at least one API model with 'security' term")
        
        self.assertTrue(len(search_model(CyberChallenge, term='web')) > 0, 
                        "Should find at least one challenge with 'web' term")
        
        # Test with 'cybersecurity' instead of just 'cyber'
        cyber_results = search_model(Article, term='cybersecurity')
        print(f"\nArticle search with 'cybersecurity' found {len(cyber_results)} results")
        self.assertTrue(len(cyber_results) > 0, 
                        "Should find at least one article with 'cybersecurity' term")

if __name__ == "__main__":
    # Run the test case
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'test', 'test_search_model_with_data.SearchModelWithDataTestCase', '-v', '2']) 