from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid


class ChatSession(models.Model):
    """Tracks individual chat sessions with users"""
    session_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions')
    created_at = models.DateTimeField(default=timezone.now)
    last_interaction = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.user:
            return f"Chat Session {self.session_id} - {self.user.email}"
        return f"Chat Session {self.session_id} - Guest"


class ChatMessage(models.Model):
    """Stores individual messages within a chat session"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    is_bot = models.BooleanField(default=False)  # True for bot messages, False for user messages
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{'Bot' if self.is_bot else 'User'} message at {self.timestamp}"


class CompanyInformation(models.Model):
    """Stores general company information for the chatbot to reference"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    keywords = models.TextField(help_text="Comma-separated keywords for search matching")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class FAQ(models.Model):
    """Stores frequently asked questions and their answers"""
    question = models.TextField()
    answer = models.TextField()
    keywords = models.TextField(help_text="Comma-separated keywords for search matching")
    category = models.CharField(max_length=100)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question


class Project(models.Model):
    """Stores information about company projects"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    keywords = models.TextField(help_text="Comma-separated keywords for search matching")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ProductService(models.Model):
    """Stores information about products and services offered"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100)
    features = models.TextField()
    keywords = models.TextField(help_text="Comma-separated keywords for search matching")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PageContent(models.Model):
    """Stores content from various pages for the chatbot to search and retrieve"""
    title = models.CharField(max_length=200)
    page_path = models.CharField(max_length=255, help_text="Path to the page (e.g., /appattack/main)")
    section = models.CharField(max_length=100, help_text="Section of the page (e.g., header, introduction, etc.)")
    content = models.TextField()
    keywords = models.TextField(help_text="Comma-separated keywords for search matching")
    page_category = models.CharField(max_length=100, help_text="Category of page (e.g., appattack, challenges, etc.)")
    priority = models.IntegerField(default=0, help_text="Higher priority content will be shown first (0-10)")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.page_path}"

    @classmethod
    def create_default_entries(cls):
        """Create default entries for the chatbot to use"""
        # Project Overview with high priority
        cls.objects.get_or_create(
            title="Project Overview",
            page_path="/pages/what_we_do",
            section="overview",
            content="""Hey there! Looking to dive into some exciting cybersecurity projects? We've got some amazing opportunities for you! Here's what we're working on:

1. AppAttack - Perfect for those who love web security and want to learn about vulnerabilities
2. DeakinThreatmirror - For the data visualization enthusiasts who want to see threats in action
3. Smishing Detection - If you're interested in mobile security and machine learning
4. Malware Visualization - For those who want to understand malware behavior in a visual way
5. VR Security Training - Experience cybersecurity training in a whole new dimension
6. PT GUI - A great starting point for aspiring penetration testers

Each project has its own dedicated page with more details. You can join any project after signing up and logging in. Which one catches your interest?""",
            keywords="projects, AppAttack, DeakinThreatmirror, Smishing, Malware, VR, PT GUI, cybersecurity, training",
            page_category="projects",
            priority=10
        )

        # Add any other default entries here if needed
        pass


class CustomChatbotResponse(models.Model):
    """Stores custom responses for the chatbot based on keywords"""
    keywords = models.TextField(help_text="Comma-separated keywords that will trigger this response")
    response = models.TextField(help_text="The response that the chatbot should give when keywords are matched")
    priority = models.IntegerField(default=0, help_text="Higher priority responses will be checked first (0-10)")
    is_active = models.BooleanField(default=True, help_text="Whether this custom response is currently active")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, 
                              help_text="Associate this response with a specific project (optional)")
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = "Custom Chatbot Response"
        verbose_name_plural = "Custom Chatbot Responses"

    def __str__(self):
        return f"Response for: {self.keywords[:50]}..." 