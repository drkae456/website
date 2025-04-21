from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
import re
from .models import FAQ, PageContent, ChatSession, ChatMessage
from home.models import (
    CyberChallenge,
    Project,
    Course,
    Skill,
    Article,
    Job,
    Announcement,
    Experience
)
import uuid
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
import datetime
from . import search_engine
from django.conf import settings
import hashlib
import time
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.utils.crypto import constant_time_compare
import logging
from functools import wraps
from .search_engine import format_model_response, verify_search_connection
from django.utils import timezone
from django.http import HttpResponse

# Add CORS headers decorator
def add_cors_headers(view_func):
    """Add CORS headers to all responses"""
    def wrapped_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        # If using OPTIONS request (preflight), return appropriate CORS headers
        if request.method == 'OPTIONS':
            r = HttpResponse()
            r['Access-Control-Allow-Origin'] = settings.CORS_ALLOWED_ORIGINS[0]  # Use the first allowed origin
            r['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
            r['Access-Control-Allow-Headers'] = 'Content-Type, X-Timestamp, X-Signature'
            r['Access-Control-Allow-Credentials'] = 'true'
            return r
            
        # For regular requests, add CORS headers to the actual response
        if isinstance(response, HttpResponse):
            origin = request.META.get('HTTP_ORIGIN', '')
            # Check if the origin is in the allowed list
            if origin in settings.CORS_ALLOWED_ORIGINS:
                response['Access-Control-Allow-Origin'] = origin
            else:
                # Default to the first allowed origin if the requesting origin is not in the list
                response['Access-Control-Allow-Origin'] = settings.CORS_ALLOWED_ORIGINS[0]
            response['Access-Control-Allow-Credentials'] = 'true'
            
        return response
    return wrapped_view

# Set up logging
logger = logging.getLogger(__name__)

# Security helper functions
def generate_api_signature(session_id, timestamp, secret_key=None):
    """
    Generate a signature for API requests to prevent tampering
    
    Args:
        session_id (str): The session ID
        timestamp (str): Current timestamp
        secret_key (str): Secret key for signature (defaults to settings.SECRET_KEY)
        
    Returns:
        str: Hex digest signature
    """
    if secret_key is None:
        secret_key = settings.SECRET_KEY
        
    message = f"{session_id}:{timestamp}:{secret_key}".encode()
    return hashlib.sha256(message).hexdigest()

def validate_api_request(request, session_id):
    """
    Validate an API request's signature and timestamp
    
    Args:
        request: The HTTP request
        session_id (str): The session ID from the URL
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Get request headers
    timestamp = request.META.get('HTTP_X_TIMESTAMP')
    client_signature = request.META.get('HTTP_X_SIGNATURE')
    
    # If security headers are not present, check if we're in debug mode
    if (not timestamp or not client_signature) and settings.DEBUG:
        return True
        
    # In production, require security headers
    if not timestamp or not client_signature:
        return False
        
    # Check if timestamp is recent (within 5 minutes)
    try:
        timestamp_int = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - timestamp_int) > 300:  # 5 minutes
            return False
    except (ValueError, TypeError):
        return False
        
    # Generate server-side signature and compare
    server_signature = generate_api_signature(session_id, timestamp)
    return constant_time_compare(client_signature, server_signature)

def api_auth_required(view_func):
    """
    Decorator to require API authentication
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        session_id = kwargs.get('session_id')
        
        # Skip validation for session creation endpoint
        if view_func.__name__ == 'session_create_api':
            return view_func(request, *args, **kwargs)
            
        # For other endpoints, validate the request
        if session_id and validate_api_request(request, session_id):
            return view_func(request, *args, **kwargs)
            
        # Return 401 for failed validation
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    return wrapped_view

def extract_keywords(message):
    """Extract keywords from the message (legacy function)"""
    # Use the new search engine module
    return search_engine.extract_project_keywords(message)

def format_page_content(page_results, keywords):
    """Format page content results into a readable response (legacy function)"""
    
    # Define project responses (ensure this is defined or passed correctly)
    project_responses = {
            'appattack': """Oh, you're interested in AppAttack? That's awesome! 🚀 AppAttack is perfect for anyone who's passionate about web security and application development. It's like a playground for learning about real-world vulnerabilities!<br><br>Here's what makes it special:<br>• 🎯 Interactive challenges that feel like real-world scenarios<br>• 📊 Progress tracking to see how you're improving<br>• 👥 Team collaboration features to learn with others<br>• 💡 Detailed feedback to help you grow<br>• 🛡️ Real-world vulnerability testing<br>• 🔍 Hands-on security experience<br><br>🎯 Perfect for:<br>• Web developers<br>• Security enthusiasts<br>• Problem solvers<br>• Team players<br>• Anyone interested in web security!<br><br>🔗 <a href="/appattack/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join AppAttack')">How to join AppAttack</button>""",

            'pt_gui': """Oh, you're interested in the Deakin Detonator Toolkit (DDT)? That's fantastic! 🛠️ This project is perfect for those who want to get hands-on with penetration testing in a user-friendly way. It's like having a Swiss Army knife for security testing!<br><br>Here's what makes DDT special:<br>• 🎯 44+ pen-testing tools at your fingertips<br>• 💻 User-friendly GUI interface<br>• 🚀 Built with Tauri, React, and Mantine<br>• 🐍 Python-powered automation<br>• 📚 12 HackTheBox walkthroughs included<br>• 🔧 Streamlined workflow automation<br><br>🎯 Key Features:<br>• Automated vulnerability scanning<br>• Manual testing tools<br>• Report generation<br>• Simplified command execution<br>• Interactive tool interfaces<br>• Comprehensive documentation<br><br>💪 Available Tools Include:<br>• Nmap for network scanning<br>• SMB Enumeration tools<br>• Shodan API integration<br>• JohnTheRipper & Hashcat<br>• Hydra for password attacks<br>• Many more security tools!<br><br>🔗 <a href="/pt_gui/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join PT GUI')">How to join PT GUI</button>""",

            'smishing_detection': """Ah, Smishing Detection! 🛡️ This is a super relevant project in today's mobile-first world. We're revolutionizing mobile security!<br><br>Here's what makes it exciting:<br>• 🔍 AI-powered SMS threat detection<br>• 📱 Works on both Android and iOS<br>• ⚡ Real-time protection<br>• 🤖 Machine learning algorithms<br>• 🛡️ User-friendly security<br>• 🌐 Global anti-scam initiative<br><br>🎯 Key Features:<br>• Real-time SMS analysis<br>• Machine learning detection<br>• Instant threat notifications<br>• Smart message analysis<br>• Educational resources<br>• User-friendly interface<br><br>💪 What it protects against:<br>• Phishing SMS attempts<br>• Malicious URLs<br>• Scam messages<br>• Social engineering attacks<br>• Data theft attempts<br><br>🔗 <a href="/smishing_detection/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join Smishing Detection')">How to join Smishing Detection</button>""",

            'malware_visualization': """Oh, you're curious about Malware Visualization? That's awesome! 🔍🔮<br><br>🚨 Malware Visualization is like the Sherlock Holmes of cybersecurity — it helps you see the invisible threats hiding in your system through smart, interactive visual tools. Whether you're a cyber pro or just malware-curious, this platform gives you the power to uncover and understand malware patterns in a whole new way.<br><br>Here's what makes it special:<br>• 📊 User-friendly visual analysis of malware activity<br>• 🤖 AI-enhanced detection for both known and novel threats<br>• 💡 No need for deep technical expertise to get started<br>• 🌐 Integrates with tools like MapBox & Leaflet.js for dynamic interaction<br>• 📈 A dashboard preview that shows malware trends clearly<br>• 💪 Built to foster collaboration within the security community<br><br>🚨 Project Goals include:<br>• Creating a sleek, powerful tool for malware analysis<br>• Improving how threats are found and removed<br>• Making cybersecurity more accessible and efficient<br>• Encouraging tech community involvement<br><br>🔧 Wanna see the tool in action?<br>Check out the <a href="/malware_visualization/project_delivery" class="learn-more-link">Project Delivery here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join Malware Visualization')">How to join Malware Visualization</button>""",

            'vr': """VR Security Training? Now we're talking! 🎮 This is perfect for those who want to experience cybersecurity training in a whole new dimension. It's like being in a cybersecurity action movie!<br><br>Here's what makes it revolutionary:<br>• 🕶️ Immersive VR learning experiences<br>• 🎯 Real-world scenario simulations<br>• 🏢 Small business focused training<br>• 🛡️ Interactive security challenges<br>• 📚 Comprehensive learning modules<br>• 🤝 Industry-aligned content<br><br>🎯 Training Modules:<br>• Password security mastery<br>• Data encryption practices<br>• Network security setup<br>• Safe web browsing habits<br>• Phishing attack recognition<br>• Wi-Fi security configuration<br><br>💪 Key Benefits:<br>• Virtual security scenarios<br>• Hands-on training<br>• Team-based challenges<br>• Progress tracking<br>• Real-time feedback<br>• Measurable outcomes<br><br>🔗 <a href="/Vr/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join VR Security')">How to join VR Security</button>""",

            'deakin_threatmirror': """DeakinThreatmirror? Now that's a fascinating project! 🎯 It's perfect for those who love turning complex data into beautiful, understandable visualizations. Think of it as a crystal ball for cybersecurity threats!<br><br>Here's what makes it special:<br>• 🎯 Open-source threat intelligence platform<br>• 📊 Advanced visual analytics for threat data<br>• 🤖 Machine learning-powered insights<br>• 🌐 Perfect for SMEs and developing economies<br>• 💡 User-friendly interface for complex data<br>• 🔄 Real-time threat feed aggregation<br><br>🎯 Project Goals:<br>• Revolutionize threat analysis and understanding<br>• Make cybersecurity accessible for smaller organizations<br>• Transform raw data into actionable intelligence<br>• Support developing economies with cost-effective solutions<br><br>💪 Key Benefits:<br>• Real-time threat data visualization<br>• Interactive maps and dashboards<br>• Customizable threat analysis<br>• Cost-effective solutions<br>• Easy-to-understand insights<br>• Community-driven development<br><br>🔗 <a href="/DeakinThreatmirror/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join DeakinThreatmirror')">How to join DeakinThreatmirror</button>"""
    }

    # --- NEW LOGIC START ---
    # Prioritize specific project responses based on keywords from the user's message
    project_keys = project_responses.keys()
    matched_key = None
    if keywords: # Check if keywords list is not empty
        for keyword in keywords:
            # Use lower() for case-insensitive matching against dictionary keys
            if keyword.lower() in project_keys:
                matched_key = keyword.lower()
                break # Found the first specific project keyword match

    if matched_key:
        return project_responses[matched_key]
    # --- NEW LOGIC END ---

    # If no specific project keyword matched, proceed with database results
    # Sort results by priority (highest first)
    sorted_results = sorted(page_results, key=lambda x: (-x.priority, x.title))
    
    # Take only the highest priority result from the database query
    if sorted_results:
        page = sorted_results[0]
        
        # --- REMOVED REDUNDANT CHECK ---
        # # Check if this page path matches a specific project (This is now less reliable)
        # for project_key, response in project_responses.items():
        #     if project_key in page.page_path.lower():
        #         return response
        # --- END REMOVED CHECK ---

        # If not a specific project (based on keyword check above), use the default response format
        # Use the content from the highest priority database result
        content = page.content.replace(f"Check out more details at {page.page_path}", "").strip()
        response = f"Hardie Hat 🤖: {content}<br><br>"
        
        if page.page_path:
            response += f'<a href="{page.page_path}" class="learn-more-link">🔗 Learn more here 🔗</a><br><br>'
        
        # Determine project name for suggestion button
        project_name = "Projects" # Default
        if hasattr(page, 'page_category') and page.page_category:
             project_name = page.page_category.replace('_', ' ').title()
        elif page.page_path and len(page.page_path.split('/')) > 2:
             project_name = page.page_path.split('/')[-2].replace('_', ' ').title()
        
        # Add suggested question
        response += '<div class="suggested-questions"><br>'
        response += '<p>Suggested question:</p><br>'
        response += f'<button class="suggestion-btn" onclick="sendMessage(\'Want to join {project_name}\')">Want to join {project_name}</button><br>'
        response += '</div>'
        
        return response.strip()
        
    return "" # Return empty if no keyword match and no page results

@csrf_exempt
@add_cors_headers
def chat_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip().lower()
            session_id = data.get('session_id', None)

            # Special handling for join requests
            if message.startswith('how to join'):
                response_text = """To join our projects, here's what you need to do:<br><br>1. First, you'll need an account:<br> 
                If you already have an account, <a href="/accounts/login/" class="learn-more-link">Sign in here</a>
                <br>   or  If you're new, <a href="/accounts/signup/" class="learn-more-link">Create an account here</a><br>
                <br>2. Once you're signed in or up :<br> Fill in your details and preferences<br> Submit your application<br><br>We'll review your preferences and get back to you with project allocation details!<br>
                <br>Need Any More Help? You can ask me anything about the process!"""
                return JsonResponse({'response': response_text})

            # Check for predefined project responses
            project_responses = {
                'appattack': """Oh, you're interested in AppAttack? That's awesome! 🚀 AppAttack is perfect for anyone who's passionate about web security and application development. It's like a playground for learning about real-world vulnerabilities!<br><br>Here's what makes it special:<br>• 🎯 Interactive challenges that feel like real-world scenarios<br>• 📊 Progress tracking to see how you're improving<br>• 👥 Team collaboration features to learn with others<br>• 💡 Detailed feedback to help you grow<br>• 🛡️ Real-world vulnerability testing<br>• 🔍 Hands-on security experience<br><br>🎯 Perfect for:<br>• Web developers<br>• Security enthusiasts<br>• Problem solvers<br>• Team players<br>• Anyone interested in web security!<br><br>🔗 <a href="/appattack/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join AppAttack')">How to join AppAttack</button>""",

                'pt_gui': """Oh, you're interested in the Deakin Detonator Toolkit (DDT)? That's fantastic! 🛠️ This project is perfect for those who want to get hands-on with penetration testing in a user-friendly way. It's like having a Swiss Army knife for security testing!<br><br>Here's what makes DDT special:<br>• 🎯 44+ pen-testing tools at your fingertips<br>• 💻 User-friendly GUI interface<br>• 🚀 Built with Tauri, React, and Mantine<br>• 🐍 Python-powered automation<br>• 📚 12 HackTheBox walkthroughs included<br>• 🔧 Streamlined workflow automation<br><br>🎯 Key Features:<br>• Automated vulnerability scanning<br>• Manual testing tools<br>• Report generation<br>• Simplified command execution<br>• Interactive tool interfaces<br>• Comprehensive documentation<br><br>💪 Available Tools Include:<br>• Nmap for network scanning<br>• SMB Enumeration tools<br>• Shodan API integration<br>• JohnTheRipper & Hashcat<br>• Hydra for password attacks<br>• Many more security tools!<br><br>🔗 <a href="/pt_gui/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join PT GUI')">How to join PT GUI</button>""",

                'smishing_detection': """Ah, Smishing Detection! 🛡️ This is a super relevant project in today's mobile-first world. We're revolutionizing mobile security!<br><br>Here's what makes it exciting:<br>• 🔍 AI-powered SMS threat detection<br>• 📱 Works on both Android and iOS<br>• ⚡ Real-time protection<br>• 🤖 Machine learning algorithms<br>• 🛡️ User-friendly security<br>• 🌐 Global anti-scam initiative<br><br>🎯 Key Features:<br>• Real-time SMS analysis<br>• Machine learning detection<br>• Instant threat notifications<br>• Smart message analysis<br>• Educational resources<br>• User-friendly interface<br><br>💪 What it protects against:<br>• Phishing SMS attempts<br>• Malicious URLs<br>• Scam messages<br>• Social engineering attacks<br>• Data theft attempts<br><br>🔗 <a href="/smishing_detection/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join Smishing Detection')">How to join Smishing Detection</button>""",

                'malware_visualization': """Oh, you're curious about Malware Visualization? That's awesome! 🔍🔮<br><br>🚨 Malware Visualization is like the Sherlock Holmes of cybersecurity — it helps you see the invisible threats hiding in your system through smart, interactive visual tools. Whether you're a cyber pro or just malware-curious, this platform gives you the power to uncover and understand malware patterns in a whole new way.<br><br>Here's what makes it special:<br>• 📊 User-friendly visual analysis of malware activity<br>• 🤖 AI-enhanced detection for both known and novel threats<br>• 💡 No need for deep technical expertise to get started<br>• 🌐 Integrates with tools like MapBox & Leaflet.js for dynamic interaction<br>• 📈 A dashboard preview that shows malware trends clearly<br>• 💪 Built to foster collaboration within the security community<br><br>🚨 Project Goals include:<br>• Creating a sleek, powerful tool for malware analysis<br>• Improving how threats are found and removed<br>• Making cybersecurity more accessible and efficient<br>• Encouraging tech community involvement<br><br>🔧 Wanna see the tool in action?<br>Check out the <a href="/malware_visualization/project_delivery" class="learn-more-link">Project Delivery here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join Malware Visualization')">How to join Malware Visualization</button>""",

                'vr': """VR Security Training? Now we're talking! 🎮 This is perfect for those who want to experience cybersecurity training in a whole new dimension. It's like being in a cybersecurity action movie!<br><br>Here's what makes it revolutionary:<br>• 🕶️ Immersive VR learning experiences<br>• 🎯 Real-world scenario simulations<br>• 🏢 Small business focused training<br>• 🛡️ Interactive security challenges<br>• 📚 Comprehensive learning modules<br>• 🤝 Industry-aligned content<br><br>🎯 Training Modules:<br>• Password security mastery<br>• Data encryption practices<br>• Network security setup<br>• Safe web browsing habits<br>• Phishing attack recognition<br>• Wi-Fi security configuration<br><br>💪 Key Benefits:<br>• Virtual security scenarios<br>• Hands-on training<br>• Team-based challenges<br>• Progress tracking<br>• Real-time feedback<br>• Measurable outcomes<br><br>🔗 <a href="/Vr/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join VR Security')">How to join VR Security</button>""",

                'deakin_threatmirror': """DeakinThreatmirror? Now that's a fascinating project! 🎯 It's perfect for those who love turning complex data into beautiful, understandable visualizations. Think of it as a crystal ball for cybersecurity threats!<br><br>Here's what makes it special:<br>• 🎯 Open-source threat intelligence platform<br>• 📊 Advanced visual analytics for threat data<br>• 🤖 Machine learning-powered insights<br>• 🌐 Perfect for SMEs and developing economies<br>• 💡 User-friendly interface for complex data<br>• 🔄 Real-time threat feed aggregation<br><br>🎯 Project Goals:<br>• Revolutionize threat analysis and understanding<br>• Make cybersecurity accessible for smaller organizations<br>• Transform raw data into actionable intelligence<br>• Support developing economies with cost-effective solutions<br><br>💪 Key Benefits:<br>• Real-time threat data visualization<br>• Interactive maps and dashboards<br>• Customizable threat analysis<br>• Cost-effective solutions<br>• Easy-to-understand insights<br>• Community-driven development<br><br>🔗 <a href="/DeakinThreatmirror/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join DeakinThreatmirror')">How to join DeakinThreatmirror</button>"""
            }

            # First check for predefined responses
            found_predefined = False
            for project_key, response in project_responses.items():
                # Check for variations of the project name
                variations = [
                    project_key,
                    project_key.replace('_', ' '),
                    project_key.replace('_', '-'),
                    project_key.upper(),
                    project_key.title()
                ]
                
                # Check if any variation is in the message
                if any(var in message for var in variations):
                    found_predefined = True
                    return JsonResponse({'response': response})

            # If no predefined response was found, use the search engine
            if not found_predefined:
                try:
                    # Process query and log the steps
                    logger.info(f"No predefined response found. Searching database for: {message}")
                    processed_query = search_engine.preprocess_query(message)
                    
                    # Search the database
                    search_results = search_engine.search_database(processed_query)
                    
                    # If search found results, format them
                    if search_results.get('results'):
                        logger.info("Search results found. Formatting response...")
                        response_text = search_engine.format_search_results(search_results, message)
                    else:
                        logger.info("No search results found.")
                        response_text = f"""I couldn't find specific information about '{message}'. Can you try rephrasing your question or ask about one of our main projects?<br><br>Here are some topics you might be interested in:<br>
                        • <button class="suggestion-btn" onclick="sendMessage('Tell me about AppAttack')">AppAttack</button><br>
                        • <button class="suggestion-btn" onclick="sendMessage('Tell me about PT GUI')">PT GUI</button><br>
                        • <button class="suggestion-btn" onclick="sendMessage('Tell me about Smishing Detection')">Smishing Detection</button>"""
                    
                    return JsonResponse({'response': response_text})
                    
                except Exception as search_error:
                    # Log detailed search error
                    logger.error(f"Search engine error: {str(search_error)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Return a fallback response
                    response_text = """I'm having trouble searching right now. Please try asking about our main projects like AppAttack, DeakinThreatmirror, or PT GUI."""
                    return JsonResponse({'response': response_text})

        except Exception as e:
            logger.error(f"Error in chat_view: {str(e)}")
            return JsonResponse({'error': 'An error occurred while processing your request.'}, status=500)

    # Handle GET requests (e.g., initial page load)
    return render(request, 'chatbot_app/chat.html', {
        'initial_message': 'Hello! Welcome to Hardhat Enterprises. How can I assist you today?'
    }) 

# New API endpoints
@csrf_exempt
@require_http_methods(["POST"])
@add_cors_headers
def session_create_api(request):
    """API endpoint to create a new chat session"""
    session_id = str(uuid.uuid4())
    
    # Create a new session in the database
    session = ChatSession.objects.create(
        session_id=session_id,
        is_active=True
    )
    
    return JsonResponse({
        'session_id': session_id,
        'created_at': session.created_at.isoformat(),
        'status': 'active'
    }, status=201)

@csrf_exempt
@require_http_methods(["GET", "DELETE"])
@add_cors_headers
def session_detail_api(request, session_id):
    """API endpoint to get session details or deactivate it"""
    try:
        session = ChatSession.objects.get(session_id=session_id)
        
        if request.method == "DELETE":
            session.is_active = False
            session.save()
            return JsonResponse({'status': 'success', 'message': 'Session deactivated'})
        
        return JsonResponse({
            'session_id': session.session_id,
            'created_at': session.created_at.isoformat(),
            'last_interaction': session.last_interaction.isoformat(),
            'status': 'active' if session.is_active else 'inactive',
            'message_count': session.messages.count()
        })
        
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

@csrf_exempt
@require_http_methods(["POST", "GET"])
@add_cors_headers
def message_api(request, session_id):
    """API endpoint to send a message to the chatbot and get a response"""
    try:
        session = ChatSession.objects.get(session_id=session_id, is_active=True)
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Active session not found'}, status=404)
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'error': 'Message cannot be empty'}, status=400)
            
            # Save user message to database
            ChatMessage.objects.create(
                session=session,
                is_user_message=True,
                message=user_message
            )
            
            # Special handling for join requests
            if user_message.lower().startswith('how to join'):
                response_text = """To join our projects, here's what you need to do:<br><br>1. First, you'll need an account:<br> 
                If you already have an account, <a href="/accounts/login/" class="learn-more-link">Sign in here</a>
                <br>   or  If you're new, <a href="/accounts/signup/" class="learn-more-link">Create an account here</a><br>
                <br>2. Once you're signed in or up :<br> Fill in your details and preferences<br> Submit your application<br><br>We'll review your preferences and get back to you with project allocation details!<br>
                <br>Need Any More Help? You can ask me anything about the process!"""
            else:
                # Use the search engine to process the query
                search_results = search_engine.process_query(user_message)
                
                # Format the search results into a response
                response_text = search_engine.format_search_results(search_results, user_message)
            
            # Save bot response to database
            bot_message = ChatMessage.objects.create(
                session=session,
                is_user_message=False,
                message=response_text
            )
            
            # Update session last interaction time
            session.last_interaction = datetime.datetime.now()
            session.save()
            
            return JsonResponse({
                'session_id': session_id,
                'message_id': bot_message.id,
                'response': response_text,
                'timestamp': bot_message.timestamp.isoformat()
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    elif request.method == "GET":
        # Return the most recent message in this session
        latest_message = ChatMessage.objects.filter(session=session).order_by('-timestamp').first()
        
        if latest_message:
            return JsonResponse({
                'message_id': latest_message.id,
                'content': latest_message.message,
                'is_user_message': latest_message.is_user_message,
                'timestamp': latest_message.timestamp.isoformat()
            })
        else:
            return JsonResponse({'message': 'No messages found'}, status=404)

@csrf_exempt
@require_http_methods(["GET"])
@add_cors_headers
def verify_connection(request):
    """
    Verify the chatbot's connection to the database.
    Returns a JSON response indicating the connection status.
    """
    try:
        # Use the enhanced search connection verification
        connection_status = search_engine.verify_search_connection()
        
        # Test database connection by creating a test session
        test_session = ChatSession.objects.create(
            session_id=str(uuid.uuid4()),
            is_active=True
        )
        test_session.delete()  # Clean up test session
        
        # If database connection was successful, update the status
        if connection_status["status"] in ["success", "partial"]:
            return JsonResponse({
                'status': connection_status["status"],
                'message': connection_status["message"],
                'timestamp': timezone.now().isoformat(),
                'diagnostics': connection_status.get("diagnostics", {})
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': connection_status["message"],
                'timestamp': timezone.now().isoformat(),
                'diagnostics': connection_status.get("diagnostics", {})
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error verifying connection: {str(e)}',
            'timestamp': timezone.now().isoformat(),
            'error_type': type(e).__name__
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@add_cors_headers
def history_api(request, session_id):
    """API endpoint to retrieve chat history for a session"""
    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
    # Get all messages for this session
    messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
    
    # Format messages for response
    message_list = [{
        'message_id': msg.id,
        'content': msg.message,
        'is_user_message': msg.is_user_message,
        'timestamp': msg.timestamp.isoformat()
    } for msg in messages]
    
    return JsonResponse({
        'session_id': session_id,
        'message_count': len(message_list),
        'created_at': session.created_at.isoformat(),
        'last_interaction': session.last_interaction.isoformat(),
        'status': 'active' if session.is_active else 'inactive',
        'messages': message_list
    }) 