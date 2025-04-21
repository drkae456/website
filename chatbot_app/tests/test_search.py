from django.test import TestCase
from chatbot_app import search_engine
from home.models import (Experience, Project, Course, Skill, Job, Article, 
                        Announcement, CyberChallenge, User)
from django.utils import timezone
import logging
import json

class SearchEngineTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Create a test user first
        self.test_user = User.objects.create(
            email="test@deakin.edu.au",
            first_name="Test",
            last_name="User",
            is_active=True
        )
        
        # Create test data for each category
        self.experience1 = Experience.objects.create(
            name="Bryce Bacon",
            feedback="He has experience in devops",
            created_at=timezone.now()
        )
        
        self.project1 = Project.objects.create(
            title='AppAttack',  # Must match exactly with PROJECT_CHOICES
            is_active=True
        )
        
        self.challenge1 = CyberChallenge.objects.create(
            title="SQL Injection Challenge",
            description="Learn about SQL injection attacks",
            question="What is SQL injection?",
            choices={"a": "Option A", "b": "Option B"},
            correct_answer="a",
            explanation="SQL injection is...",
            difficulty="medium",
            category="web",
            points=10
        )
        
        self.course1 = Course.objects.create(
            title="Cybersecurity Fundamentals",
            code="SIT123",
            is_active=True
        )
        
        self.skill1 = Skill.objects.create(
            name="Penetration Testing",
            description="Advanced penetration testing skills",
            slug="penetration-testing"
        )
        
        self.job1 = Job.objects.create(
            title="Security Analyst",
            description="Looking for a security analyst with experience in threat detection",
            location="Remote",
            job_type="FT",
            closing_date=timezone.now() + timezone.timedelta(days=30)
        )
        
        self.article1 = Article.objects.create(
            title="Latest in Cybersecurity",
            content="Recent developments in cybersecurity landscape",
            author=self.test_user,
            featured=True
        )
        
        self.announcement1 = Announcement.objects.create(
            message="New Security Feature",
            isActive=True,
            created_at=timezone.now()
        )

    def get_item_name(self, item):
        """Helper method to get item name or title, handling both attributes and methods"""
        # Special case for Project model which uses choices
        if isinstance(item, Project):
            return item.get_title_display()
            
        # Special case for Announcement which uses message instead of title/name
        if isinstance(item, Announcement):
            return item.message
            
        for attr in ['name', 'title', 'message']:
            if hasattr(item, attr):
                value = getattr(item, attr)
                # If it's a method, call it
                if callable(value):
                    return value()
                return value
        return None

    def test_preprocess_query(self):
        """Test query preprocessing"""
        test_cases = [
            ("Experience", "experience"),  # Test case conversion
            ("User  Experience", "user experience"),  # Test extra space removal
            ("User-Experience!", "user-experience"),  # Test punctuation removal except hyphens
        ]
        
        for input_query, expected in test_cases:
            processed = search_engine.preprocess_query(input_query)
            self.assertEqual(processed, expected)

    def test_extract_general_keywords(self):
        """Test keyword extraction including special handling of 'experience'"""
        # Test that 'experience' is always included as a keyword
        keywords = search_engine.extract_general_keywords("user experience")
        self.assertIn("experience", keywords)
        
        # Test with stopwords
        keywords = search_engine.extract_general_keywords("the experience of users")
        self.assertIn("experience", keywords)
        self.assertIn("users", keywords)
        self.assertNotIn("the", keywords)
        self.assertNotIn("of", keywords)

    def test_search_database_experiences(self):
        """Test searching for experiences in the database"""
        # Test exact match
        results = search_engine.search_database("devops")
        self.assertTrue(any(item['category'] == 'experiences' for item in results['results']))
        
        # Test partial match
        results = search_engine.search_database("experience")
        self.assertTrue(any(item['category'] == 'experiences' for item in results['results']))
        
        # Test case insensitive
        results = search_engine.search_database("DEVOPS")
        self.assertTrue(any(item['category'] == 'experiences' for item in results['results']))

    def test_process_query(self):
        """Test the complete query processing pipeline"""
        # Test complete query processing
        results = search_engine.process_query("experience in devops")
        
        # Check if results were returned
        self.assertIn('query', results)
        self.assertIn('results', results)
        self.assertIn('total_results', results)
        self.assertIn('categories', results)
        
        # Check if we found any experiences
        self.assertTrue(any(item['category'] == 'experiences' for item in results['results']))

    def test_get_best_response(self):
        """Test response type selection"""
        # Create a query that should prioritize experiences
        results = search_engine.process_query("experience")
        
        # Get the best response type
        _, response_type, source_items = search_engine.get_best_response(results)
        
        # Check if experiences are properly prioritized
        self.assertEqual(response_type, 'experiences')
        self.assertTrue(len(source_items) > 0)

    def test_relevance_scoring(self):
        """Test relevance scoring for experiences"""
        # Create a query that matches experiences
        results = search_engine.process_query("experience")
        
        # Get the experiences from results
        experiences = [item for item in results['results'] if item['category'] == 'experiences']
        
        # Verify experiences are found and have relevance scores
        self.assertTrue(len(experiences) > 0)
        self.assertTrue(all('relevance_score' in exp for exp in experiences))

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Test empty query
        results = search_engine.process_query("")
        self.assertEqual(results['total_results'], 0)
        
        # Test query with only stopwords
        results = search_engine.process_query("the and in")
        self.assertEqual(results['total_results'], 0)
        
        # Test very long query
        long_query = "experience " * 100
        results = search_engine.process_query(long_query)
        self.assertTrue(results['total_results'] > 0)
        
        # Test special characters
        special_query = "experience!@#$%^&*()"
        results = search_engine.process_query(special_query)
        self.assertTrue(results['total_results'] > 0)

    def test_category_specific_searches(self):
        """Test search functionality across all categories with detailed logging"""
        
        test_cases = [
            {
                'query': "appattack web security project",
                'expected_category': 'projects',
                'expected_content': "AppAttack"
            },
            {
                'query': "devops experience Bryce",
                'expected_category': 'experiences',
                'expected_content': "Bryce Bacon"
            },
            {
                'query': "sql injection challenge",
                'expected_category': 'challenges',
                'expected_content': "SQL Injection Challenge"
            },
            {
                'query': "cybersecurity fundamentals course",
                'expected_category': 'courses',
                'expected_content': "Cybersecurity Fundamentals"
            },
            {
                'query': "penetration testing skill",
                'expected_category': 'skills',
                'expected_content': "Penetration Testing"
            },
            {
                'query': "security analyst job",
                'expected_category': 'jobs',
                'expected_content': "Security Analyst"
            },
            {
                'query': "cybersecurity article",
                'expected_category': 'articles',
                'expected_content': "Latest in Cybersecurity"
            },
            {
                'query': "new security announcement",
                'expected_category': 'announcements',
                'expected_content': "New Security Feature"
            }
        ]

        # List to collect failed tests
        failures = []
        
        for test_case in test_cases:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Testing search with query: {test_case['query']}")
            
            try:
                # Process the query
                self.logger.info("Step 1: Processing query...")
                results = search_engine.process_query(test_case['query'])
                
                # Log search results
                self.logger.info("\nStep 2: Search results:")
                for item in results['results']:
                    self.logger.info(f"Category: {item['category']}, Score: {item.get('relevance_score', 'N/A')}")
                
                # Get best response
                self.logger.info("\nStep 3: Determining best response...")
                _, response_type, source_items = search_engine.get_best_response(results)
                self.logger.info(f"Selected response type: {response_type}")
                
                # Verify response type matches expected category
                if response_type != test_case['expected_category']:
                    self.logger.warning(f"❌ Category mismatch: Expected '{test_case['expected_category']}', got '{response_type}'")
                    failures.append({
                        'query': test_case['query'],
                        'error': f"Category mismatch: Expected '{test_case['expected_category']}', got '{response_type}'",
                        'expected': test_case['expected_category'],
                        'actual': response_type
                    })
                    continue
                
                # Verify content
                found_content = False
                for item in results['results']:
                    if item['category'] == test_case['expected_category']:
                        # Check different name fields based on category
                        content = None
                        if 'name' in item:
                            content = item['name']
                        elif 'title' in item:
                            content = item['title']
                        elif 'message' in item:
                            content = item['message']
                            
                        if content and test_case['expected_content'] in content:
                            found_content = True
                            break
                
                if not found_content:
                    self.logger.warning(f"❌ Content not found: Expected to find '{test_case['expected_content']}'")
                    failures.append({
                        'query': test_case['query'],
                        'error': f"Content not found: Expected '{test_case['expected_content']}'",
                        'expected': test_case['expected_content'],
                        'actual': 'Content not found'
                    })
                    continue
                
                self.logger.info(f"✓ Test passed for {test_case['expected_category']}")
                
            except Exception as e:
                self.logger.error(f"❌ Error during test: {str(e)}")
                failures.append({
                    'query': test_case['query'],
                    'error': f"Unhandled error: {str(e)}",
                    'expected': test_case['expected_category'],
                    'actual': 'Error'
                })
            
            self.logger.info(f"{'='*50}\n")
        
        # Log a summary of all failures at the end
        if failures:
            self.logger.error("\n" + "!"*70)
            self.logger.error("TEST FAILURES SUMMARY")
            self.logger.error("!"*70)
            for i, failure in enumerate(failures, 1):
                self.logger.error(f"\nFailure #{i}:")
                self.logger.error(f"Query: {failure['query']}")
                self.logger.error(f"Error: {failure['error']}")
                self.logger.error(f"Expected: {failure['expected']}")
                self.logger.error(f"Actual: {failure['actual']}")
            self.logger.error("\n" + "!"*70)
            self.logger.error(f"Total failures: {len(failures)} out of {len(test_cases)} tests")
            self.logger.error("!"*70 + "\n")
            
            # Make the test fail if there were any failures
            self.assertEqual(len(failures), 0, f"{len(failures)} test cases failed. See log for details.")
        else:
            self.logger.info("\n" + "*"*70)
            self.logger.info("ALL TESTS PASSED SUCCESSFULLY!")
            self.logger.info("*"*70 + "\n")

    def test_admin_content_search(self):
        """Test searching for content created through admin dashboard"""
        from chatbot_app.models import FAQ, PageContent
        
        # Create test content that would typically be added through admin
        faq = FAQ.objects.create(
            question="How do I reset my password?",
            answer="You can reset your password through the account settings page",
            category="account",
            priority=1
        )
        
        page_content = PageContent.objects.create(
            title="Security Guidelines",
            content="Important security guidelines for all users",
            page_path="/security/guidelines",
            priority=2
        )
        
        # Test searching for FAQ content
        results = search_engine.search_database("reset password")
        self.assertTrue(any(
            item['category'] == 'faq' and 
            'reset' in item['content'].lower() and
            'password' in item['content'].lower()
            for item in results['results']
        ))
        
        # Test searching for page content
        results = search_engine.search_database("security guidelines")
        self.assertTrue(any(
            item['category'] == 'page_content' and
            'security' in item['content'].lower() and
            'guidelines' in item['content'].lower()
            for item in results['results']
        ))
        
        # Test priority-based sorting
        results = search_engine.search_database("security")
        sorted_results = sorted(
            [r for r in results['results'] if r['category'] in ['faq', 'page_content']], 
            key=lambda x: x.get('priority', 0),
            reverse=True
        )
        self.assertEqual(len(sorted_results), 1)
        self.assertEqual(sorted_results[0]['category'], 'page_content')

    def test_dynamic_content_updates(self):
        """Test that search results update when admin content is modified"""
        from chatbot_app.models import FAQ
        
        # Create initial FAQ
        faq = FAQ.objects.create(
            question="What are the system requirements?",
            answer="Minimum requirements include 8GB RAM",
            category="technical",
            priority=1
        )
        
        # Initial search
        results = search_engine.search_database("system requirements")
        initial_count = len([r for r in results['results'] if r['category'] == 'faq'])
        
        # Update FAQ
        faq.answer = "Updated: Minimum requirements include 16GB RAM"
        faq.save()
        
        # Search again and verify updated content is found
        results = search_engine.search_database("system requirements")
        self.assertTrue(any(
            item['category'] == 'faq' and 
            '16GB' in item['content']
            for item in results['results']
        ))
        
        # Delete FAQ and verify it's no longer in results
        faq.delete()
        results = search_engine.search_database("system requirements")
        self.assertEqual(
            len([r for r in results['results'] if r['category'] == 'faq']),
            0
        )

    def test_multiple_content_types(self):
        """Test searching across multiple content types simultaneously"""
        from chatbot_app.models import FAQ, PageContent
        
        # Create various types of content
        faq = FAQ.objects.create(
            question="What security measures are in place?",
            answer="We implement multiple layers of security",
            category="security",
            priority=1
        )
        
        page = PageContent.objects.create(
            title="Security Overview",
            content="Our security measures include encryption",
            page_path="/security/overview",
            priority=2
        )
        
        project = Project.objects.create(
            title="Security Project",
            description="A project focused on security",
            is_active=True
        )
        
        # Search for "security" across all content types
        results = search_engine.search_database("security")
        
        # Verify we find content across different types
        categories_found = set(item['category'] for item in results['results'])
        self.assertTrue(len(categories_found) >= 3)  # Should find at least FAQ, PageContent, and Project
        
        # Verify relevance scoring works across types
        self.assertTrue(all('relevance_score' in item for item in results['results']))
        
        # Verify results are properly sorted by relevance
        scores = [item.get('relevance_score', 0) for item in results['results']]
        self.assertEqual(scores, sorted(scores, reverse=True)) 