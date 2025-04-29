import logging
from django.test import TestCase
from chatbot_app import search_engine
from chatbot_app.models import FAQ, PageContent
from home.models import (
   Project,
    Course,
    Skill,
    Progress,
    Contact,
    ContactSubmission,
    Experience,

    Webpage,
    DDT_contact,
    #Feedback,
    Job,
    JobApplication,
    
    # Contact_central,
    Article,
    Smishingdetection_join_us,
    Projects_join_us,
    CyberChallenge,
    UserChallenge,
    Announcement,

    # Logging
    SecurityEvent,

    #LeaderBaord
    LeaderBoardTable
)

# Configure logging for tests
logging.disable(logging.CRITICAL)

class SingleWordPromptTests(TestCase):
    """
    Tests the chatbot's response to single-word prompts mapping to specific models.
    Verifies that the response contains information about the first few entries
    from the corresponding database table.
    """

    @classmethod
    def setUpTestData(cls):
        cls.setup_errors = [] # List to collect setup errors
        test_user = None # Initialize test_user

        # Wrap each model creation block in try-except
        try:
            Project.objects.create(title="Test Project 1")
            Project.objects.create(title="Test Project 2")
            Project.objects.create(title="Test Project 3")
            Project.objects.create(title="Test Project 4") # More than 3
        except Exception as e:
            cls.setup_errors.append(("Project", e))

        try:
            Course.objects.create(title="Test Course 1", code="C1")
            Course.objects.create(title="Test Course 2", code="C2")
        except Exception as e:
            cls.setup_errors.append(("Course", e))

        try:
            Skill.objects.create(name="Test Skill 1", description="Skill Desc 1")
            Skill.objects.create(name="Test Skill 2", description="Skill Desc 2")
            Skill.objects.create(name="Test Skill 3", description="Skill Desc 3")
        except Exception as e:
            cls.setup_errors.append(("Skill", e))

        try:
            Experience.objects.create(name="User 1", feedback="Exp 1")
            Experience.objects.create(name="User 2", feedback="Exp 2")
            Experience.objects.create(name="User 3", feedback="Exp 3")
        except Exception as e:
            cls.setup_errors.append(("Experience", e))

        try:
            # Jobs need closing_date and HTML description
            from django.utils import timezone
            import datetime
            from tinymce.models import HTMLField  # If HTMLField is used
            
            # Create date one month in the future for closing_date
            future_date = timezone.now() + datetime.timedelta(days=30)
            
            # Check if description is HTMLField or TextField
            try:
                Job.objects.create(
                    title="Test Job 1", 
                    description="Job Desc 1",
                    location="Remote",  # Required choice field  
                    job_type="FT",  # Required choice field
                    closing_date=future_date
                )
                Job.objects.create(
                    title="Test Job 2", 
                    description="Job Desc 2",
                    location="Remote",
                    job_type="PT",
                    closing_date=future_date
                )
                Job.objects.create(
                    title="Test Job 3", 
                    description="Job Desc 3",
                    location="OnSite",
                    job_type="CT",
                    closing_date=future_date
                )
            except Exception as e_job_inner:
                # If creating with simple description fails, try with HTMLField
                from django.utils.html import format_html
                Job.objects.create(
                    title="Test Job 1", 
                    description=format_html("<p>Job Desc 1</p>"),
                    location="Remote",
                    job_type="FT",
                    closing_date=future_date
                )
                Job.objects.create(
                    title="Test Job 2", 
                    description=format_html("<p>Job Desc 2</p>"),
                    location="Remote",
                    job_type="PT",
                    closing_date=future_date
                )
                Job.objects.create(
                    title="Test Job 3", 
                    description=format_html("<p>Job Desc 3</p>"),
                    location="OnSite",
                    job_type="CT",
                    closing_date=future_date
                )
        except Exception as e:
             cls.setup_errors.append(("Job", e))

        try:
            # Create a test user for the Article author
            from django.contrib.auth import get_user_model
            User = get_user_model()
            # Use get_or_create to avoid potential errors if user already exists in complex scenarios
            test_user, created = User.objects.get_or_create(
                email="test@example.com",
                defaults={
                    'first_name': "Test",
                    'last_name': "User",
                    'is_active': True
                }
            )
            
            # Articles need an author
            Article.objects.create(title="Test Article 1", content="Art 1", author=test_user)
            Article.objects.create(title="Test Article 2", content="Art 2", author=test_user)
            Article.objects.create(title="Test Article 3", content="Art 3", author=test_user)
        except Exception as e:
            cls.setup_errors.append(("Article/User", e))

        try:
            # CyberChallenges need JSON choices and other required fields
            CyberChallenge.objects.create(
                title="Test Challenge 1", 
                description="Chal Desc 1", 
                question="Sample question 1?",
                choices={"A": "Option A", "B": "Option B", "C": "Option C"},
                correct_answer="A",
                explanation="Explanation for challenge 1", 
                difficulty="easy", 
                category="web", 
                points=10
            )
            
            CyberChallenge.objects.create(
                title="Test Challenge 2", 
                description="Chal Desc 2", 
                question="Sample question 2?",
                choices={"A": "Option A", "B": "Option B", "C": "Option C"},
                correct_answer="B",
                explanation="Explanation for challenge 2", 
                difficulty="medium", 
                category="network", 
                points=20
            )
            
            CyberChallenge.objects.create(
                title="Test Challenge 3", 
                description="Chal Desc 3", 
                question="Sample question 3?",
                choices={"A": "Option A", "B": "Option B", "C": "Option C"},
                correct_answer="C",
                explanation="Explanation for challenge 3", 
                difficulty="hard", 
                category="crypto", 
                points=30
            )
            
            CyberChallenge.objects.create(
                title="Test Challenge 4", 
                description="Chal Desc 4", 
                question="Sample question 4?",
                choices={"A": "Option A", "B": "Option B", "C": "Option C"},
                correct_answer="A",
                explanation="Explanation for challenge 4", 
                difficulty="easy", 
                category="web", 
                points=15
            )
        except Exception as e:
            cls.setup_errors.append(("CyberChallenge", e))

        try:
            Announcement.objects.create(message="Announce 1", isActive=True)
            Announcement.objects.create(message="Announce 2", isActive=True)
            Announcement.objects.create(message="Announce 3 (Inactive)", isActive=False) # Test inactive filtering
            Announcement.objects.create(message="Announce 4", isActive=True)
        except Exception as e:
            cls.setup_errors.append(("Announcement", e))

        try:
            # Add FAQ data
            FAQ.objects.create(question="Test FAQ 1?", answer="Ans 1", category="General")
            FAQ.objects.create(question="Test FAQ 2?", answer="Ans 2", category="Technical")
            FAQ.objects.create(question="Test FAQ 3?", answer="Ans 3", category="General")
        except Exception as e:
             cls.setup_errors.append(("FAQ", e))

        try:
            # Add PageContent data
            PageContent.objects.create(title="Test Page 1", content="Page Content 1", page_path="/test1", page_category="Info")
            PageContent.objects.create(title="Test Page 2", content="Page Content 2", page_path="/test2", page_category="Info")
            PageContent.objects.create(title="Test Page 3", content="Page Content 3", page_path="/test3", page_category="About")
        except Exception as e:
             cls.setup_errors.append(("PageContent", e))

        try:
            # Add Contact data
            Contact.objects.create(name="Contact User 1", email="contact1@test.com", message="Contact Message 1")
            Contact.objects.create(name="Contact User 2", email="contact2@test.com", message="Contact Message 2")
        except Exception as e:
             cls.setup_errors.append(("Contact", e))
             
        try:
            # Add DDT_contact data - requires 'mobile' field
            DDT_contact.objects.create(fullname="DDT User 1", email="ddt1@test.com", mobile="1234567890", message="DDT Message 1")
        except Exception as e:
            cls.setup_errors.append(("DDT_contact", e))

        try:
            # Add Join Us data
            Smishingdetection_join_us.objects.create(name="Smishing Joiner 1", email="smish1@test.com", message="Smishing Join 1")
        except Exception as e:
             cls.setup_errors.append(("Smishingdetection_join_us", e))
             
        try:
            Projects_join_us.objects.create(name="Project Joiner 1", email="proj1@test.com", message="Project Join 1", page_name="AppAttack")
            Projects_join_us.objects.create(name="Project Joiner 2", email="proj2@test.com", message="Project Join 2", page_name="PT_GUI")
        except Exception as e:
             cls.setup_errors.append(("Projects_join_us", e))

        # Print all collected errors at the end of setup
        if cls.setup_errors:
            print("\n--- Errors during setUpTestData ---")
            for model_name, error in cls.setup_errors:
                print(f"Model: {model_name}\nError: {error}\n---")
            # Optionally raise an exception here to stop tests if any setup failed, 
            # but the goal is to see all errors, so printing might be better.
            # raise Exception("Errors occurred during test data setup. See print output.")

    def _test_single_word_prompt(self, prompt, model, key_field, filter_kwargs=None):
        """Helper method to test a single word prompt against its model."""
        # Fetch expected results from DB (limit to 3, order by PK for consistency)
        # For Announcements, filter by isActive=True and order by creation date descending
        if model == Announcement:
            expected_objects = model.objects.filter(isActive=True).order_by('-created_at')[:3]
        else:
            # Apply filters if provided (e.g., for composite models)
            qs = model.objects.all()
            if filter_kwargs:
                qs = qs.filter(**filter_kwargs)
            expected_objects = qs.order_by('pk')[:3]

        # Simulate chatbot search
        search_results = search_engine.process_query(prompt)
        response_html = search_engine.format_search_results(search_results, prompt)

        # Check if expected items are mentioned in the response
        found_count = 0
        for obj in expected_objects:
            expected_text = getattr(obj, key_field)
            # For Announcements, the title is constructed differently
            if model == Announcement:
                # Allow for flexible matching as the title includes the date
                self.assertIn(expected_text, response_html,
                              f"Expected announcement message '{expected_text}' not found in response for prompt '{prompt}'")
                found_count += 1 # Count presence differently for announcements
            else:
                 self.assertIn(expected_text, response_html,
                           f"Expected text '{expected_text}' not found in response for prompt '{prompt}'")
                 found_count +=1

        # Assert that at least one expected item was found (handles cases with <3 items)
        self.assertGreater(found_count, 0, f"No expected items found in response for prompt '{prompt}'")
        # Optional: Assert the exact number found if necessary, considering formatting might merge items
        # self.assertEqual(found_count, len(expected_objects), f"Expected {len(expected_objects)} items, but found mentions of {found_count} in response for prompt '{prompt}'")


    def test_prompt_project(self):
        self._test_single_word_prompt("project", Project, "title")

    def test_prompt_course(self):
        self._test_single_word_prompt("course", Course, "title")

    def test_prompt_skill(self):
        self._test_single_word_prompt("skill", Skill, "name")

    # Note: Experience formatting might differ, adjust key_field if needed
    def test_prompt_experience(self):
         self._test_single_word_prompt("experience", Experience, "feedback") # Or 'name'

    def test_prompt_job(self):
        self._test_single_word_prompt("job", Job, "title")

    def test_prompt_article(self):
        self._test_single_word_prompt("article", Article, "title")

    def test_prompt_cyberchallenge(self):
        # CyberChallenge formatting uses the title and lists multiple results
        prompt = "cyberchallenge"
        expected_objects = CyberChallenge.objects.order_by('pk')[:4] # Get first 4 for this test
        search_results = search_engine.process_query(prompt)
        response_html = search_engine.format_search_results(search_results, prompt)

        found_count = 0
        for obj in expected_objects:
            # Check for title and link structure
            expected_link_text = f"<a href='/challenges/detail/{obj.id}/' class='learn-more-link'>{obj.title}</a>"
            if expected_link_text in response_html:
                found_count += 1
            # We could also check for difficulty, category, points if needed

        # Expecting the challenge-specific format to list multiple challenges
        self.assertGreaterEqual(found_count, 3, f"Expected at least 3 challenges to be listed for prompt '{prompt}', found {found_count}")


    def test_prompt_announcement(self):
        # Announcement uses the message content and filters by isActive
        self._test_single_word_prompt("announcement", Announcement, "message")

    # --- New Tests ---
    def test_prompt_faq(self):
        # Test prompt "faq" - checks against the question field by default
        self._test_single_word_prompt("faq", FAQ, "question")
        # Additionally check if the answer is present for the first FAQ
        faq1 = FAQ.objects.get(question="Test FAQ 1?")
        search_results = search_engine.process_query("faq")
        response_html = search_engine.format_search_results(search_results, "faq")
        self.assertIn(faq1.answer, response_html, "Expected answer for FAQ 1 not found in response.")


    def test_prompt_page(self):
        # Test prompt "page" - checks against title field
        self._test_single_word_prompt("page", PageContent, "title")
        # Additionally check if content and link are present for the first PageContent
        page1 = PageContent.objects.get(title="Test Page 1")
        search_results = search_engine.process_query("page")
        response_html = search_engine.format_search_results(search_results, "page")
        self.assertIn(page1.content, response_html, "Expected content for Page 1 not found.")
        if page1.page_path:
             self.assertIn(f'href="{page1.page_path}"', response_html, "Expected link for Page 1 not found.")

    def test_prompt_contact(self):
        # Test prompt "contact" - checks against message field for both Contact and DDT_contact
        # Check Contact model results
        self._test_single_word_prompt("contact", Contact, "message")
        # Check DDT_contact model results (response should contain these too if search works)
        self._test_single_word_prompt("contact", DDT_contact, "message")

        # Additionally check a specific contact message
        contact1 = Contact.objects.get(name="Contact User 1")
        search_results = search_engine.process_query("contact")
        response_html = search_engine.format_search_results(search_results, "contact")
        self.assertIn(contact1.message, response_html, "Expected message for Contact 1 not found.")

    def test_prompt_join(self):
        # Test prompt "join" - checks against message field for both Join Us models
        # Check Smishingdetection_join_us results
        self._test_single_word_prompt("join", Smishingdetection_join_us, "message")
        # Check Projects_join_us results
        self._test_single_word_prompt("join", Projects_join_us, "message")

        # Additionally check a specific join message
        join1 = Projects_join_us.objects.get(name="Project Joiner 1")
        search_results = search_engine.process_query("join")
        response_html = search_engine.format_search_results(search_results, "join")
        self.assertIn(join1.message, response_html, "Expected message for Project Joiner 1 not found.") 