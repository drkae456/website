from django.test import TestCase, Client
from django.urls import reverse
import json
from .test_search import SearchEngineTestCase
from ..models import ChatSession, ChatMessage

class ChatbotIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.search_test = SearchEngineTestCase()
        self.search_test.setUp()
        
    def test_chatbot_search_flow(self):
        """
        Test the complete flow from chatbot query to formatted response
        """
        # Create a new chat session
        response = self.client.post(reverse('create_session'))
        self.assertEqual(response.status_code, 201)
        session_id = response.json()['session_id']
        
        # Test a search query
        test_queries = [
            "Tell me about AppAttack",
            "What cybersecurity courses are available?",
            "Show me recent announcements",
            "What skills can I learn?",
            "Are there any job openings?"
        ]
        
        for query in test_queries:
            # Send message through API
            response = self.client.post(
                reverse('send_message', args=[session_id]),
                data=json.dumps({'message': query}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            
            # Verify response structure
            response_data = response.json()
            self.assertIn('response', response_data)
            self.assertIn('message_id', response_data)
            self.assertIn('timestamp', response_data)
            
            # Verify the response contains relevant information
            response_text = response_data['response']
            self.assertIsNotNone(response_text)
            self.assertNotEqual(response_text, "")
            
            # Check if the message was saved to database
            message = ChatMessage.objects.get(id=response_data['message_id'])
            self.assertEqual(message.message, response_text)
            self.assertFalse(message.is_user_message)
            
            # Verify the session was updated
            session = ChatSession.objects.get(session_id=session_id)
            self.assertTrue(session.is_active)
            
    def test_error_handling(self):
        """
        Test how the chatbot handles various error cases
        """
        # Create a new chat session
        response = self.client.post(reverse('create_session'))
        session_id = response.json()['session_id']
        
        # Test empty message
        response = self.client.post(
            reverse('send_message', args=[session_id]),
            data=json.dumps({'message': ''}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        # Test invalid JSON
        response = self.client.post(
            reverse('send_message', args=[session_id]),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        # Test non-existent session
        response = self.client.post(
            reverse('send_message', args=['invalid-session-id']),
            data=json.dumps({'message': 'test'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
        
    def test_chat_history(self):
        """
        Test that chat history is properly maintained
        """
        # Create a new chat session
        response = self.client.post(reverse('create_session'))
        session_id = response.json()['session_id']
        
        # Send multiple messages
        messages = [
            "What is AppAttack?",
            "Tell me more about it",
            "What skills are needed?"
        ]
        
        for message in messages:
            response = self.client.post(
                reverse('send_message', args=[session_id]),
                data=json.dumps({'message': message}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            
        # Get chat history
        response = self.client.get(reverse('chat_history', args=[session_id]))
        self.assertEqual(response.status_code, 200)
        
        history = response.json()
        self.assertEqual(len(history['messages']), len(messages) * 2)  # Each message has a user and bot response
        self.assertEqual(history['message_count'], len(messages) * 2)
        self.assertTrue(history['status'] == 'active')
        
        # Verify message order and content
        for i, message in enumerate(history['messages']):
            if i % 2 == 0:  # User messages
                self.assertTrue(message['is_user_message'])
                self.assertEqual(message['content'], messages[i//2])
            else:  # Bot responses
                self.assertFalse(message['is_user_message'])
                self.assertNotEqual(message['content'], "")

    def test_get_session_details(self):
        """
        Test retrieving session details
        """
        # Create a new chat session
        response = self.client.post(reverse('create_session'))
        self.assertEqual(response.status_code, 201)
        session_id = response.json()['session_id']
        
        # Get session details
        response = self.client.get(reverse('session_detail', args=[session_id]))
        self.assertEqual(response.status_code, 200)
        
        details = response.json()
        self.assertEqual(details['session_id'], session_id)
        self.assertEqual(details['status'], 'active')
        self.assertIn('created_at', details)
        self.assertIn('last_interaction', details)
        self.assertEqual(details['message_count'], 0) # No messages sent yet

        # Test non-existent session
        response = self.client.get(reverse('session_detail', args=['invalid-id']))
        self.assertEqual(response.status_code, 404)

    def test_delete_session(self):
        """
        Test deactivating (deleting) a session
        """
        # Create a new chat session
        response = self.client.post(reverse('create_session'))
        self.assertEqual(response.status_code, 201)
        session_id = response.json()['session_id']
        
        # Deactivate the session
        response = self.client.delete(reverse('session_detail', args=[session_id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Verify session is inactive in DB
        session = ChatSession.objects.get(session_id=session_id)
        self.assertFalse(session.is_active)
        
        # Try to get details of deactivated session (should still work)
        response = self.client.get(reverse('session_detail', args=[session_id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'inactive')
        
        # Try to delete non-existent session
        response = self.client.delete(reverse('session_detail', args=['invalid-id']))
        self.assertEqual(response.status_code, 404)

    def test_get_latest_message(self):
        """
        Test retrieving the latest message for a session
        """
        # Create a new chat session
        response = self.client.post(reverse('create_session'))
        self.assertEqual(response.status_code, 201)
        session_id = response.json()['session_id']
        
        # Test getting latest message when none exist
        response = self.client.get(reverse('send_message', args=[session_id]))
        self.assertEqual(response.status_code, 404)
        
        # Send a message
        user_message_content = "First message for latest check"
        response = self.client.post(
            reverse('send_message', args=[session_id]),
            data=json.dumps({'message': user_message_content}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        bot_response_content = response.json()['response']
        bot_message_id = response.json()['message_id']

        # Get the latest message (should be the bot response)
        response = self.client.get(reverse('send_message', args=[session_id]))
        self.assertEqual(response.status_code, 200)
        latest_message = response.json()
        self.assertEqual(latest_message['message_id'], bot_message_id)
        self.assertEqual(latest_message['content'], bot_response_content)
        self.assertFalse(latest_message['is_user_message'])
        
        # Test non-existent session
        response = self.client.get(reverse('send_message', args=['invalid-id']))
        self.assertEqual(response.status_code, 404)

    def test_admin_content_integration(self):
        """Test the complete flow of searching and retrieving admin-created content"""
        from chatbot_app.models import FAQ, PageContent, Project
        from django.test import Client
        import json
        
        client = Client()
        
        # Create test content that simulates admin dashboard entries
        faq = FAQ.objects.create(
            question="How do I contribute to a project?",
            answer="You can contribute by following our contribution guidelines",
            category="contribution",
            priority=1
        )
        
        page = PageContent.objects.create(
            title="Contribution Guidelines",
            content="Step by step guide for contributing to projects",
            page_path="/contribute",
            priority=1
        )
        
        project = Project.objects.create(
            title="Community Project",
            description="A project that welcomes contributions",
            is_active=True
        )
        
        # Test searching for contribution-related content
        response = client.post('/chat/', 
            data=json.dumps({
                'message': 'How can I contribute?',
                'session_id': 'test_session'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Verify response contains relevant content
        self.assertTrue(
            any('contribute' in str(item).lower() for item in data['results'])
        )
        
        # Test that response is properly formatted
        self.assertIn('response', data)
        self.assertIn('session_id', data)
        
        # Test searching with multiple keywords
        response = client.post('/chat/',
            data=json.dumps({
                'message': 'project contribution guidelines',
                'session_id': 'test_session'
            }),
            content_type='application/json'
        )
        
        data = json.loads(response.content)
        # Verify multiple content types are found
        results_categories = set(
            item['category'] for item in data['results']
            if 'category' in item
        )
        self.assertTrue(len(results_categories) >= 2)

    def test_search_result_formatting(self):
        """Test that search results are properly formatted for display"""
        from chatbot_app.models import FAQ, PageContent
        from django.test import Client
        import json
        
        client = Client()
        
        # Create test content with specific formatting requirements
        faq = FAQ.objects.create(
            question="What is the **markdown** formatting?",
            answer="You can use *italic* and **bold** text",
            category="formatting",
            priority=1
        )
        
        page = PageContent.objects.create(
            title="Formatting Guide",
            content="This is a guide with [links](http://example.com)",
            page_path="/formatting",
            priority=1
        )
        
        # Test that markdown is preserved
        response = client.post('/chat/',
            data=json.dumps({
                'message': 'markdown formatting',
                'session_id': 'test_session'
            }),
            content_type='application/json'
        )
        
        data = json.loads(response.content)
        
        # Verify markdown formatting is preserved
        self.assertTrue(
            any('**' in str(item) for item in data['results'])
        )
        
        # Verify HTML is properly escaped
        self.assertFalse(
            any('<script>' in str(item) for item in data['results'])
        )
        
        # Test response structure
        self.assertTrue(isinstance(data['response'], str))
        self.assertTrue(isinstance(data['results'], list)) 