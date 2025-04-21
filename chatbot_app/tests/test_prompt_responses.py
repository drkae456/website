from django.test import TestCase
from chatbot_app import search_engine
from home.models import (Announcement, Course, Skill, CyberChallenge, User)
from django.utils import timezone
import json

class PromptResponseTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create a test user
        self.test_user = User.objects.create(
            email="test@deakin.edu.au",
            first_name="Test",
            last_name="User",
            is_active=True
        )
        
        # Create test data for database search
        self.announcement = Announcement.objects.create(
            message="New cybersecurity course available",
            isActive=True,
            created_at=timezone.now()
        )
        
        self.course = Course.objects.create(
            title="Advanced Cybersecurity",
            code="SIT456",
            is_postgraduate=False
        )
        
        self.skill = Skill.objects.create(
            name="Penetration Testing",
            description="Learn ethical hacking techniques"
        )
        
        self.challenge = CyberChallenge.objects.create(
            title="Network Security Challenge",
            description="Test your network security knowledge",
            question="What is a firewall?",
            choices={"a": "Option A", "b": "Option B"},
            correct_answer="a",
            explanation="A firewall is...",
            difficulty="hard",
            category="network",
            points=20
        )

    def test_predefined_responses(self):
        """Test that predefined responses are returned correctly"""
        # Define some test cases with predefined responses
        test_cases = [
            {
                "prompt": "What is your name?",
                "expected_response": "I am the Deakin Cybersecurity Chatbot. How can I help you today?"
            },
            {
                "prompt": "How are you?",
                "expected_response": "I'm doing well, thank you! How can I assist you with cybersecurity today?"
            },
            {
                "prompt": "What can you help me with?",
                "expected_response": "I can help you with information about courses, skills, challenges, announcements, and more related to cybersecurity at Deakin."
            }
        ]
        
        for case in test_cases:
            response = search_engine.process_query(case["prompt"])
            self.assertEqual(response, case["expected_response"])

    def test_database_search_fallback(self):
        """Test that queries without predefined responses trigger database search"""
        test_cases = [
            {
                "prompt": "Tell me about announcements",
                "expected_keywords": ["announcement", "update"],
                "expected_content": "New cybersecurity course available"
            },
            {
                "prompt": "What cybersecurity courses are available?",
                "expected_keywords": ["course", "cybersecurity"],
                "expected_content": "Advanced Cybersecurity"
            },
            {
                "prompt": "What skills can I learn?",
                "expected_keywords": ["skill", "learn"],
                "expected_content": "Penetration Testing"
            },
            {
                "prompt": "Tell me about challenges",
                "expected_keywords": ["challenge", "network"],
                "expected_content": "Network Security Challenge"
            }
        ]
        
        for case in test_cases:
            response = search_engine.process_query(case["prompt"])
            # Verify the response contains expected keywords and content
            self.assertIsNotNone(response)
            self.assertNotEqual(response, "")
            for keyword in case["expected_keywords"]:
                self.assertIn(keyword.lower(), response.lower())
            self.assertIn(case["expected_content"], response)

    def test_mixed_queries(self):
        """Test queries that might match both predefined responses and database content"""
        test_cases = [
            {
                "prompt": "What is cybersecurity?",
                "should_be_predefined": True
            },
            {
                "prompt": "Show me cybersecurity courses",
                "should_be_predefined": False
            },
            {
                "prompt": "Hello",
                "should_be_predefined": True
            },
            {
                "prompt": "What skills are available?",
                "should_be_predefined": False
            }
        ]
        
        for case in test_cases:
            response = search_engine.process_query(case["prompt"])
            self.assertIsNotNone(response)
            self.assertNotEqual(response, "")
            
            if case["should_be_predefined"]:
                # For predefined responses, verify it's not a database search result
                self.assertNotIn(self.course.title, response)
                self.assertNotIn(self.skill.name, response)
                self.assertNotIn(self.challenge.title, response)
            else:
                # For database searches, verify it contains relevant content
                self.assertTrue(
                    any(content in response for content in [
                        self.course.title,
                        self.skill.name,
                        self.challenge.title,
                        self.announcement.message
                    ])
                )

    def test_keyword_matching(self):
        """Test that keyword matching works correctly for database searches"""
        test_cases = [
            {
                "prompt": "I want to learn about hacking",
                "expected_matches": ["Penetration Testing"]
            },
            {
                "prompt": "Are there any new updates?",
                "expected_matches": ["New cybersecurity course available"]
            },
            {
                "prompt": "What network security topics are covered?",
                "expected_matches": ["Network Security Challenge"]
            }
        ]
        
        for case in test_cases:
            response = search_engine.process_query(case["prompt"])
            self.assertIsNotNone(response)
            for expected_match in case["expected_matches"]:
                self.assertIn(expected_match, response) 