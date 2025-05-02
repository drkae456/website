import pytest
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from home.models import (
    Announcement,
    Article,
    Course,
    CyberChallenge,
    Experience,
    Job,
    LeaderBoardTable,
    Project,
    Skill,
    SecurityEvent
)
from chatbot_app.search_engine import search

class TestModelNameQueries(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user first
        User = get_user_model()
        test_user = User.objects.create(
            email="test@example.com",
            first_name="Test",
            last_name="User"
        )
        
        # Create test data for each model
        Announcement.objects.create(
            message="Test announcement message",
            isActive=True,
            created_at=timezone.now()
        )
        
        Article.objects.create(
            title="Test Article",
            content="Test article content",
            author=test_user,
            featured=True
        )
        
        Course.objects.create(
            title="Test Course",
            code="TST101",
            is_active=True
        )
        
        CyberChallenge.objects.create(
            title="Test Challenge",
            description="Test challenge description",
            question="Test question",
            choices={"a": "Option A", "b": "Option B"},
            correct_answer="a",
            explanation="Test explanation",
            difficulty="easy",
            category="general",
            points=10
        )
        
        Experience.objects.create(
            name="Test User",
            feedback="Test feedback",
            created_at=timezone.now()
        )
        
        Job.objects.create(
            title="Test Job",
            description="Test job description",
            location="Remote",
            job_type="FT",
            closing_date=timezone.now().date()
        )
        
        LeaderBoardTable.objects.create(
            user=test_user,
            category="General",
            total_points=100
        )
        
        Project.objects.create(
            title="AppAttack",
            is_active=True
        )
        
        Skill.objects.create(
            name="Test Skill",
            description="Test skill description",
            slug="test-skill"
        )
        
        SecurityEvent.objects.create(
            event_type="Test Event",
            description="Test security event",
            timestamp=timezone.now()
        )

    def test_single_keyword_queries(self):
        """Test that single keyword queries for model names return appropriate results"""
        test_cases = [
            ("announcements", "announcement"),
            ("articles", "article"),
            ("challenges", "challenge"),
            ("courses", "course"),
            ("experiences", "experience"),
            ("jobs", "job"),
            ("leaderboard", "leaderboard"),
            ("projects", "project"),
            ("skills", "skill"),
            ("security", "security event")
        ]
        
        for query, expected_keyword in test_cases:
            with self.subTest(query=query):
                result = search(query)
                self.assertIsNotNone(result)
                self.assertIn(expected_keyword.lower(), result.lower(),
                    f"Expected to find '{expected_keyword}' in response for query '{query}'")

    def test_informal_queries(self):
        """Test informal variations of model name queries"""
        test_cases = [
            ("show me any announcements", "announcement"),
            ("list all articles", "article"),
            ("what challenges are there", "challenge"),
            ("available courses", "course"),
            ("any experiences", "experience"),
            ("current jobs", "job"),
            ("show leaderboard", "leaderboard"),
            ("active projects", "project"),
            ("required skills", "skill"),
            ("recent security events", "security event")
        ]
        
        for query, expected_keyword in test_cases:
            with self.subTest(query=query):
                result = search(query)
                self.assertIsNotNone(result)
                self.assertIn(expected_keyword.lower(), result.lower(),
                    f"Expected to find '{expected_keyword}' in response for query '{query}'")

    def test_case_insensitivity(self):
        """Test that queries are case insensitive"""
        test_cases = [
            ("ANNOUNCEMENTS", "announcements"),
            ("Courses", "courses"),
            ("JOBS", "jobs"),
            ("Skills", "skills"),
            ("SECURITY EVENTS", "security_events"),
        ]

        for query, expected_key in test_cases:
            results = search(query)
            self.assertIsNotNone(results)
            self.assertIn(expected_key, results)
            self.assertGreaterEqual(len(results[expected_key]), 1)

    def test_plural_singular_forms(self):
        """Test both plural and singular forms of model names"""
        test_cases = [
            ("announcement", "announcements"),
            ("announcements", "announcements"),
            ("job", "jobs"),
            ("jobs", "jobs"),
            ("skill", "skills"),
            ("skills", "skills"),
            ("course", "courses"),
            ("courses", "courses"),
        ]

        for query, expected_key in test_cases:
            results = search(query)
            self.assertIsNotNone(results)
            self.assertIn(expected_key, results)
            self.assertGreaterEqual(len(results[expected_key]), 1) 