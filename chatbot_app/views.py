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
from django.contrib.auth.decorators import login_required

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
logger.setLevel(logging.DEBUG)  # Set to DEBUG level to see all logs

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

# Define project responses
project_responses = {
    'appattack': """Oh, you're interested in AppAttack? That's awesome! 🚀 AppAttack is perfect for anyone who's passionate about web security and application development. It's like a playground for learning about real-world vulnerabilities!<br><br>Here's what makes it special:<br>• 🎯 Interactive challenges that feel like real-world scenarios<br>• 📊 Progress tracking to see how you're improving<br>• 👥 Team collaboration features to learn with others<br>• 💡 Detailed feedback to help you grow<br>• 🛡️ Real-world vulnerability testing<br>• 🔍 Hands-on security experience<br><br>🎯 Perfect for:<br>• Web developers<br>• Security enthusiasts<br>• Problem solvers<br>• Team players<br>• Anyone interested in web security!<br><br>🔗 <a href="/appattack/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join AppAttack')">How to join AppAttack</button>""",

    'pt_gui': """Oh, you're interested in the Deakin Detonator Toolkit (DDT)? That's fantastic! 🛠️ This project is perfect for those who want to get hands-on with penetration testing in a user-friendly way. It's like having a Swiss Army knife for security testing!<br><br>Here's what makes DDT special:<br>• 🎯 44+ pen-testing tools at your fingertips<br>• 💻 User-friendly GUI interface<br>• 🚀 Built with Tauri, React, and Mantine<br>• 🐍 Python-powered automation<br>• 📚 12 HackTheBox walkthroughs included<br>• 🔧 Streamlined workflow automation<br><br>🎯 Key Features:<br>• Automated vulnerability scanning<br>• Manual testing tools<br>• Report generation<br>• Simplified command execution<br>• Interactive tool interfaces<br>• Comprehensive documentation<br><br>💪 Available Tools Include:<br>• Nmap for network scanning<br>• SMB Enumeration tools<br>• Shodan API integration<br>• JohnTheRipper & Hashcat<br>• Hydra for password attacks<br>• Many more security tools!<br><br>🔗 <a href="/pt_gui/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join PT GUI')">How to join PT GUI</button>""",

    'smishing_detection': """Ah, Smishing Detection! 🛡️ This is a super relevant project in today's mobile-first world. We're revolutionizing mobile security!<br><br>Here's what makes it exciting:<br>• 🔍 AI-powered SMS threat detection<br>• 📱 Works on both Android and iOS<br>• ⚡ Real-time protection<br>• 🤖 Machine learning algorithms<br>• 🛡️ User-friendly security<br>• 🌐 Global anti-scam initiative<br><br>🎯 Key Features:<br>• Real-time SMS analysis<br>• Machine learning detection<br>• Instant threat notifications<br>• Smart message analysis<br>• Educational resources<br>• User-friendly interface<br><br>💪 What it protects against:<br>• Phishing SMS attempts<br>• Malicious URLs<br>• Scam messages<br>• Social engineering attacks<br>• Data theft attempts<br><br>🔗 <a href="/smishing_detection/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join Smishing Detection')">How to join Smishing Detection</button>""",

    'malware_visualization': """Oh, you're curious about Malware Visualization? That's awesome! 🔍🔮<br><br>🚨 Malware Visualization is like the Sherlock Holmes of cybersecurity — it helps you see the invisible threats hiding in your system through smart, interactive visual tools. Whether you're a cyber pro or just malware-curious, this platform gives you the power to uncover and understand malware patterns in a whole new way.<br><br>Here's what makes it special:<br>• 📊 User-friendly visual analysis of malware activity<br>• 🤖 AI-enhanced detection for both known and novel threats<br>• 💡 No need for deep technical expertise to get started<br>• 🌐 Integrates with tools like MapBox & Leaflet.js for dynamic interaction<br>• 📈 A dashboard preview that shows malware trends clearly<br>• 💪 Built to foster collaboration within the security community<br><br>🚨 Project Goals include:<br>• Creating a sleek, powerful tool for malware analysis<br>• Improving how threats are found and removed<br>• Making cybersecurity more accessible and efficient<br>• Encouraging tech community involvement<br><br>🔧 Wanna see the tool in action?<br>Check out the <a href="/malware_visualization/project_delivery" class="learn-more-link">Project Delivery here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join Malware Visualization')">How to join Malware Visualization</button>""",

    'vr': """VR Security Training? Now we're talking! 🎮 This is perfect for those who want to experience cybersecurity training in a whole new dimension. It's like being in a cybersecurity action movie!<br><br>Here's what makes it revolutionary:<br>• 🕶️ Immersive VR learning experiences<br>• 🎯 Real-world scenario simulations<br>• 🏢 Small business focused training<br>• 🛡️ Interactive security challenges<br>• 📚 Comprehensive learning modules<br>• 🤝 Industry-aligned content<br><br>🎯 Training Modules:<br>• Password security mastery<br>• Data encryption practices<br>• Network security setup<br>• Safe web browsing habits<br>• Phishing attack recognition<br>• Wi-Fi security configuration<br><br>💪 Key Benefits:<br>• Virtual security scenarios<br>• Hands-on training<br>• Team-based challenges<br>• Progress tracking<br>• Real-time feedback<br>• Measurable outcomes<br><br>🔗 <a href="/Vr/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join VR Security')">How to join VR Security</button>""",

    'deakin_threatmirror': """DeakinThreatmirror? Now that's a fascinating project! 🎯 It's perfect for those who love turning complex data into beautiful, understandable visualizations. Think of it as a crystal ball for cybersecurity threats!<br><br>Here's what makes it special:<br>• 🎯 Open-source threat intelligence platform<br>• 📊 Advanced visual analytics for threat data<br>• 🤖 Machine learning-powered insights<br>• 🌐 Perfect for SMEs and developing economies<br>• 💡 User-friendly interface for complex data<br>• 🔄 Real-time threat feed aggregation<br><br>🎯 Project Goals:<br>• Revolutionize threat analysis and understanding<br>• Make cybersecurity accessible for smaller organizations<br>• Transform raw data into actionable intelligence<br>• Support developing economies with cost-effective solutions<br><br>💪 Key Benefits:<br>• Real-time threat data visualization<br>• Interactive maps and dashboards<br>• Customizable threat analysis<br>• Cost-effective solutions<br>• Easy-to-understand insights<br>• Community-driven development<br><br>🔗 <a href="/DeakinThreatmirror/main" class="learn-more-link">Learn more here</a><br><br>Want to get involved? Try asking:<br><button class="suggestion-btn" onclick="sendMessage('how to join DeakinThreatmirror')">How to join DeakinThreatmirror</button>"""
}

@csrf_exempt
@add_cors_headers
def chat_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            session_id = data.get('session_id')
            
            # Get user info from request payload
            user_info = data.get('user_info', {})
            is_authenticated = user_info.get('is_authenticated', False)
            username = user_info.get('username', 'Guest')
            user_id = user_info.get('user_id')
            
            # Verify auth token if provided
            auth_token = user_info.get('auth_token')
            auth_timestamp = user_info.get('auth_timestamp')
            token_verified = False
            
            if is_authenticated and auth_token and auth_timestamp and user_id:
                import hashlib
                # Recreate the token on this server to verify
                token_data = f"{user_id}:{auth_timestamp}:{settings.SECRET_KEY}"
                server_token = hashlib.sha256(token_data.encode()).hexdigest()
                
                # Verify token
                if server_token == auth_token:
                    # Check if token is not too old (10 minutes validity)
                    current_time = int(time.time())
                    token_age = current_time - int(auth_timestamp)
                    if token_age < 600:  # 10 minutes
                        token_verified = True
                        logger.info(f"Auth token verified for user {username}")
                    else:
                        logger.warning(f"Auth token expired for user {username}")
                else:
                    logger.warning(f"Auth token verification failed for user {username}")
            
            # If token verification failed but user claims to be authenticated, treat as guest
            if is_authenticated and not token_verified:
                is_authenticated = False
                username = 'Guest'
                user_id = None
                logger.warning("User claimed to be authenticated but token verification failed")
            
            logger.info(f"\n{'='*50}\nReceived chat message: '{message}'")
            logger.debug(f"Session ID from request: {session_id}")
            logger.debug(f"User info from request: {user_info}")
            logger.debug(f"Auth verified: {token_verified}")
            
            personalized_greeting = f"Hi {username}! "
            
            if not message:
                logger.warning("Empty message received")
                return JsonResponse({
                    'response': f"{personalized_greeting}I didn't receive any message. How can I help you?",
                    'session_id': session_id,
                    'typing_delay': 2000
                })
            
            # --- Robust Session Handling ---
            session = None
            new_session_id_created = False
            
            if session_id:
                try:
                    # Get existing session
                    session = ChatSession.objects.filter(session_id=session_id).first()
                    
                    if session:
                        # Update user association if authenticated
                        if is_authenticated and user_id:
                            from django.contrib.auth import get_user_model
                            User = get_user_model()
                            try:
                                user_obj = User.objects.get(id=user_id)
                                # Only update user if it changed
                                if session.user != user_obj:
                                    session.user = user_obj
                                    session.save(update_fields=['user'])
                                    logger.info(f"Updated session {session_id} with user {username}")
                            except User.DoesNotExist:
                                logger.warning(f"User ID {user_id} not found")
                    else:
                        # Create new session
                        if is_authenticated and user_id:
                            from django.contrib.auth import get_user_model
                            User = get_user_model()
                            try:
                                user_obj = User.objects.get(id=user_id)
                                session = ChatSession.objects.create(session_id=session_id, user=user_obj)
                            except User.DoesNotExist:
                                session = ChatSession.objects.create(session_id=session_id)
                        else:
                            session = ChatSession.objects.create(session_id=session_id)
                        
                        new_session_id_created = True
                except Exception as e:
                    logger.error(f"Error handling session: {str(e)}")
                    session = ChatSession.objects.create()
                    session_id = session.session_id
                    new_session_id_created = True
            else:
                # No session ID provided, create new one
                session = ChatSession.objects.create()
                session_id = session.session_id
                new_session_id_created = True
            
            # --- End Robust Session Handling ---

            # Try fuzzy spell correction first
            from .search_engine import spell_correct
            corrected_message, was_corrected = spell_correct(message)
            if was_corrected:
                logger.info(f"Spell correction applied: '{message}' -> '{corrected_message}'")
                message_for_matching = corrected_message
            else:
                message_for_matching = message

            message_lower = message_for_matching.lower()
            response_text = None # Placeholder for the final bot response text

            # First try direct project name matching in the message
            for project_key, specific_response in project_responses.items():
                project_key_norm = project_key.lower()
                if (project_key_norm in message_lower or
                    f"{project_key_norm} project" in message_lower or
                    f"about {project_key_norm}" in message_lower or
                    f"what is {project_key_norm}" in message_lower or
                    f"what's {project_key_norm}" in message_lower or
                    f"tell me about {project_key_norm}" in message_lower or
                    (project_key == "pt_gui" and ("pt gui" in message_lower or "ddt" in message_lower or "deakin detonator" in message_lower)) or
                    (project_key == "deakin_threatmirror" and "threatmirror" in message_lower) or
                    (project_key == "appattack" and "app attack" in message_lower) or
                    (project_key == "smishing_detection" and "smishing" in message_lower) or
                    (project_key == "malware_visualization" and "malware" in message_lower) or
                    (project_key == "vr" and "vr security" in message_lower)):

                    logger.debug(f"Direct match found for project: {project_key}")
                    response_text = specific_response
                    break # Exit loop once match found

            # If no direct match, try fuzzy matching with project keys
            if response_text is None:
                import difflib
                project_keys = list(project_responses.keys())
                words_in_message = message_lower.split()
                for word in words_in_message:
                    if len(word) < 4: continue
                    matches = difflib.get_close_matches(word, project_keys, n=1, cutoff=0.7)
                    if matches:
                        matched_key = matches[0]
                        similarity = difflib.SequenceMatcher(None, word, matched_key).ratio()
                        logger.debug(f"Fuzzy match found: '{word}' -> '{matched_key}' (similarity: {similarity:.2f})")
                        response_text = f"I think you're asking about <em>{matched_key}</em>.<br><br>" + project_responses[matched_key]
                        break # Exit loop once match found

            # If no matches yet, try keyword extraction for projects
            if response_text is None:
                project_keywords = extract_keywords(message_for_matching)
                if project_keywords:
                     for keyword in project_keywords:
                        for project_key in project_responses.keys():
                            if keyword.lower() == project_key.lower():
                                logger.debug(f"Keyword extraction match found: {keyword} -> {project_key}")
                                response_text = project_responses[project_key]
                                break # Exit inner loop
                        if response_text: break # Exit outer loop

            # If still no response, proceed with general search
            if response_text is None:
                logger.info("No predefined response found, using search engine")
                try:
                    search_results = search_engine.search(message, user_email=user_info.get('user_email'))
                    logger.info(f"Got search results for '{message}'")
                    response_text = search_results # Assuming search returns formatted text
                except Exception as e:
                    logger.error(f"Search error: {str(e)}")
                    response_text = "I'm sorry, but I encountered an error while processing your request. Please try again."

            # --- Save messages ---
            try:
                # Save user message
                ChatMessage.objects.create(
                    session=session,
                    message=message, # Original message
                    is_bot=False
                )
                # Save bot response
                ChatMessage.objects.create(
                    session=session,
                    message=response_text,
                    is_bot=True
                )
                logger.debug(f"Saved messages to database for session {session_id}")
            except Exception as e:
                logger.error(f"Error saving messages to database for session {session_id}: {str(e)}")
            # --- End Save messages ---

            # --- Prepare final response ---
            final_response_content = ""
            if was_corrected:
                final_response_content += f"Showing results for <em>{corrected_message}</em> instead of '{message}'.<br><br>"

            # Add personalized greeting only if it's the start of the effective response
            # (Check if response_text already includes greetings potentially)
            # For simplicity now, let's always prepend unless it's an error message starting with "I'm sorry"
            if not response_text.startswith("I'm sorry"):
                 final_response_content = personalized_greeting + final_response_content + response_text
            else:
                 final_response_content += response_text # Keep error messages clean

            return JsonResponse({
                'response': final_response_content,
                'session_id': session_id, # Return the potentially new session ID
                'typing_delay': 2000
            })

        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return JsonResponse({'error': "Invalid request format"}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in chat_view: {str(e)}")
            return JsonResponse({'error': "An unexpected server error occurred."}, status=500)

    # For GET requests, render the chat page
    return render(request, 'chatbot/chat.html', {'project_name': 'Hardie Hat Chat'})

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
        is_active=True,
        user=request.user if request.user.is_authenticated else None
    )
    
    return JsonResponse({
        'session_id': session_id,
        'created_at': session.created_at.isoformat(),
        'status': 'active',
        'is_authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else 'Guest'
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
@api_auth_required
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
                is_bot=False,  # User message
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
                is_bot=True,  # Bot response
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
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return JsonResponse({'error': 'An error occurred while processing your message'}, status=500)
    
    elif request.method == "GET":
        # Return the most recent message in this session
        latest_message = ChatMessage.objects.filter(session=session).order_by('-timestamp').first()
        
        if latest_message:
            return JsonResponse({
                'message_id': latest_message.id,
                'content': latest_message.message,
                'is_bot': latest_message.is_bot,  # Use is_bot
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
        'is_bot': msg.is_bot,
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

@csrf_exempt
@add_cors_headers
def test_logging(request):
    """
    Test endpoint to verify logging functionality
    """
    logger.debug("This is a DEBUG level message")
    logger.info("This is an INFO level message")
    logger.warning("This is a WARNING level message")
    logger.error("This is an ERROR level message")
    
    # Test database query logging
    from .models import ChatSession
    ChatSession.objects.count()
    
    return JsonResponse({
        'status': 'success',
        'message': 'Logging test completed. Check your console for logs.'
    })

def test_fuzzy_search(request):
    """
    Test view for fuzzy search functionality
    """
    try:
        # Get test query from request
        query = request.GET.get('query', '')
        
        # Test fuzzy search
        results = search_engine.search_database(query)
        
        return JsonResponse({
            'status': 'success',
            'query': query,
            'results': results,
            'original_query': query,
            'corrected_query': results.get('corrected_query', query)
        })
        
    except Exception as e:
        logger.error(f"Error in test_fuzzy_search: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def analyze_fuzzy_search(request):
    """
    A detailed view that shows exactly how the fuzzy matching works for a query
    Access via /analyze-fuzzy/?q=your+misspelled+query
    
    Shows detailed word-by-word analysis of spelling corrections
    """
    import json
    import difflib
    from django.http import JsonResponse
    from .search_engine import preprocess_query, preprocess_text, STOPWORDS, spell_correct
    
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({
            'error': 'Missing query parameter. Use ?q=your+search+query'
        })
    
    # Preprocess the query
    preprocessed_query = preprocess_query(query)
    
    # Get the corrected query
    corrected_query, was_corrected = spell_correct(query)
    
    # Analyze each word with detailed similarity scores
    words = query.split()
    word_analysis = []
    
    # Get the vocabulary from the spell_correct function
    from .search_engine import get_document_corpus
    from home.models import Project, CyberChallenge, Course
    
    # Build a vocabulary for analysis
    vocabulary = []
    
    # Add project names and keywords
    try:
        for project in Project.objects.all():
            if project.name:
                vocabulary.append(project.name.lower())
            if project.keywords:
                vocabulary.extend([k.strip().lower() for k in project.keywords.split(',')])
    except Exception as e:
        pass
    
    # Add challenge questions and categories
    try:
        for challenge in CyberChallenge.objects.all():
            if challenge.question:
                vocabulary.append(challenge.question.lower())
            if challenge.category:
                vocabulary.append(challenge.category.lower())
    except Exception as e:
        pass
    
    # Add course titles and codes
    try:
        for course in Course.objects.all():
            if course.title:
                vocabulary.append(course.title.lower())
            if course.code:
                vocabulary.append(course.code.lower())
    except Exception as e:
        pass
    
    # Add domain terms
    domain_terms = [
        'security', 'cyber', 'cyberattack', 'cybersecurity', 'attack', 'defense',
        'vulnerability', 'exploit', 'malware', 'virus', 'trojan', 'ransomware',
        'phishing', 'smishing', 'authentication', 'authorization', 'encryption',
        'decryption', 'penetration', 'testing', 'pentest', 'hacking', 'ethical',
        'firewall', 'intrusion', 'detection', 'prevention', 'deakin', 'university',
        'course', 'project', 'challenge', 'ctf', 'capture', 'flag'
    ]
    vocabulary.extend(domain_terms)
    
    # Create a unique vocabulary
    vocabulary = list(set(vocabulary))
    
    # Analyze each word
    for word in words:
        word_info = {
            'original': word,
            'length': len(word),
            'is_stopword': word.lower() in STOPWORDS,
            'is_too_short': len(word) <= 3,
            'top_matches': []
        }
        
        # Only analyze words that would be processed
        if len(word) > 3 and word.lower() not in STOPWORDS:
            # Get top matches
            matches = difflib.get_close_matches(word.lower(), vocabulary, n=5, cutoff=0.5)
            
            # Calculate similarity scores
            for match in matches:
                similarity = difflib.SequenceMatcher(None, word.lower(), match).ratio()
                word_info['top_matches'].append({
                    'word': match,
                    'similarity': similarity,
                    'would_be_selected': similarity >= 0.7 and match == matches[0]
                })
            
            # Sort by similarity
            word_info['top_matches'].sort(key=lambda x: x['similarity'], reverse=True)
            
            # Add corrected word info
            if word_info['top_matches'] and word_info['top_matches'][0]['similarity'] >= 0.7:
                word_info['corrected_to'] = word_info['top_matches'][0]['word']
                word_info['was_corrected'] = word_info['corrected_to'] != word.lower()
            else:
                word_info['corrected_to'] = word
                word_info['was_corrected'] = False
        else:
            # Not eligible for correction
            word_info['corrected_to'] = word
            word_info['was_corrected'] = False
            if word_info['is_stopword']:
                word_info['reason'] = 'Stopword'
            elif word_info['is_too_short']:
                word_info['reason'] = 'Too short'
        
        word_analysis.append(word_info)
    
    # Format the analysis as HTML
    html_response = f"""
    <html>
    <head>
        <title>Fuzzy Search Analysis: {query}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .word-card {{ 
                border: 1px solid #ddd; 
                border-radius: 5px; 
                padding: 15px; 
                margin-bottom: 15px;
                background-color: #f9f9f9;
            }}
            .corrected {{ background-color: #e6ffe6; }}
            .match-table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin-top: 10px;
            }}
            .match-table th, .match-table td {{ 
                border: 1px solid #ddd; 
                padding: 8px; 
                text-align: left;
            }}
            .match-table th {{ 
                background-color: #f2f2f2; 
            }}
            .selected {{ 
                background-color: #e6ffe6; 
                font-weight: bold;
            }}
            .summary {{
                background-color: #f0f0f0;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .vocab-sample {{
                max-height: 200px;
                overflow-y: auto;
                border: 1px solid #ddd;
                padding: 10px;
                margin-top: 10px;
                background-color: white;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Fuzzy Search Analysis</h1>
            
            <div class="summary">
                <h2>Query Summary</h2>
                <p><strong>Original query:</strong> "{query}"</p>
                <p><strong>Preprocessed query:</strong> "{preprocessed_query}"</p>
                <p><strong>Corrected query:</strong> "{corrected_query}"</p>
                <p><strong>Was corrected:</strong> {was_corrected}</p>
                <p><strong>Vocabulary size:</strong> {len(vocabulary)} terms</p>
                
                <h3>Vocabulary Sample</h3>
                <div class="vocab-sample">
                    <ul>
                        {"".join(f"<li>{term}</li>" for term in sorted(vocabulary)[:100])}
                        {f"<li>... and {len(vocabulary) - 100} more terms</li>" if len(vocabulary) > 100 else ""}
                    </ul>
                </div>
            </div>
            
            <h2>Word-by-Word Analysis</h2>
    """
    
    for word_info in word_analysis:
        card_class = "word-card"
        if word_info.get('was_corrected', False):
            card_class += " corrected"
            
        html_response += f"""
            <div class="{card_class}">
                <h3>Word: "{word_info['original']}"</h3>
                <p><strong>Length:</strong> {word_info['length']}</p>
        """
        
        if word_info.get('is_stopword', False):
            html_response += f"""
                <p><strong>Status:</strong> Stopword (not eligible for correction)</p>
            """
        elif word_info.get('is_too_short', False):
            html_response += f"""
                <p><strong>Status:</strong> Too short (not eligible for correction)</p>
            """
        else:
            was_corrected = word_info.get('was_corrected', False)
            corrected_to = word_info.get('corrected_to', word_info['original'])
            
            if was_corrected:
                html_response += f"""
                    <p><strong>Status:</strong> Corrected from "{word_info['original']}" to "{corrected_to}"</p>
                """
            else:
                html_response += f"""
                    <p><strong>Status:</strong> No correction needed or no suitable match found</p>
                """
            
            # Add matches table
            if word_info['top_matches']:
                html_response += f"""
                    <h4>Top Matches:</h4>
                    <table class="match-table">
                        <tr>
                            <th>Word</th>
                            <th>Similarity</th>
                            <th>Status</th>
                        </tr>
                """
                
                for match in word_info['top_matches']:
                    row_class = "selected" if match.get('would_be_selected', False) else ""
                    status = "Selected for correction" if match.get('would_be_selected', False) else "Not selected"
                    
                    html_response += f"""
                        <tr class="{row_class}">
                            <td>{match['word']}</td>
                            <td>{match['similarity']:.4f} ({int(match['similarity'] * 100)}%)</td>
                            <td>{status}</td>
                        </tr>
                    """
                
                html_response += """
                    </table>
                """
            else:
                html_response += """
                    <p><strong>Matches:</strong> No matches found in vocabulary</p>
                """
        
        html_response += """
            </div>
        """
    
    html_response += """
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html_response)

def test_search_page(request):
    """
    A simple interface for testing search queries and viewing results
    """
    from .search_engine import process_query, format_search_results
    
    query = request.GET.get('q', '')
    results = None
    formatted_response = None
    was_corrected = False
    corrected_query = None
    
    if query:
        # Process the query
        results = process_query(query)
        
        # Get the formatted response
        formatted_response = format_search_results(results, query)
        
        # Check if query was corrected
        was_corrected = 'corrected_query' in results
        corrected_query = results.get('corrected_query')
    
    # Create the HTML response - avoid nested f-strings by breaking it up
    html_start = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Search Engine Test</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
            h1, h2, h3 {
                color: #333;
            }
            .search-form {
                margin-bottom: 20px;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 5px;
            }
            input[type="text"] {
                padding: 10px;
                width: 70%;
                border: 1px solid #ddd;
                border-radius: 3px;
                font-size: 16px;
            }
            button {
                padding: 10px 15px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                cursor: pointer;
                font-size: 16px;
            }
            .results-container {
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
            }
            .results-box {
                flex: 1;
                min-width: 300px;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                background-color: #f9f9f9;
                margin-bottom: 20px;
            }
            .formatted-response {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                background-color: white;
                margin-top: 10px;
            }
            .json-display {
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 3px;
                overflow-x: auto;
                font-family: monospace;
                white-space: pre-wrap;
                max-height: 500px;
                overflow-y: auto;
            }
            .correction-notice {
                background-color: #e7f3fe;
                border-left: 3px solid #2196F3;
                padding: 10px;
                margin-bottom: 15px;
            }
            .test-queries {
                margin-top: 20px;
            }
            .test-queries a {
                display: inline-block;
                margin: 5px;
                padding: 5px 10px;
                background-color: #eee;
                border-radius: 3px;
                text-decoration: none;
                color: #333;
            }
            .test-queries a:hover {
                background-color: #ddd;
            }
            .sql-container {
                margin-top: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                background-color: #f9f9f9;
            }
            .sql-query {
                background-color: #272822;
                color: #f8f8f2;
                padding: 10px;
                border-radius: 3px;
                margin: 10px 0;
                overflow-x: auto;
                font-family: monospace;
            }
            .query-info {
                display: flex;
                justify-content: space-between;
                background-color: #eee;
                padding: 5px 10px;
                border-radius: 3px 3px 0 0;
                font-size: 12px;
            }
            .result-count {
                font-weight: bold;
                color: #4CAF50;
            }
            .time-taken {
                font-style: italic;
                color: #666;
            }
            .orm-query {
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 0 0 3px 3px;
                font-family: monospace;
                border-top: none;
                font-size: 12px;
            }
            .tab-container {
                margin-top: 20px;
            }
            .tab {
                overflow: hidden;
                border: 1px solid #ccc;
                background-color: #f1f1f1;
                border-radius: 5px 5px 0 0;
            }
            .tab button {
                background-color: inherit;
                float: left;
                border: none;
                outline: none;
                cursor: pointer;
                padding: 10px 16px;
                transition: 0.3s;
                color: #333;
            }
            .tab button:hover {
                background-color: #ddd;
            }
            .tab button.active {
                background-color: #4CAF50;
                color: white;
            }
            .tabcontent {
                display: none;
                padding: 15px;
                border: 1px solid #ccc;
                border-top: none;
                border-radius: 0 0 5px 5px;
            }
            .tabcontent.active {
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Search Engine Test Page</h1>
    """
    
    # Add the search form with the query value
    search_form = f"""
            <div class="search-form">
                <form method="GET" action="">
                    <input type="text" name="q" value="{query}" placeholder="Enter your search query..." />
                    <button type="submit">Search</button>
                </form>
                
                <div class="test-queries">
                    <h3>Try these test queries:</h3>
                    <a href="?q=appatack">appatack</a>
                    <a href="?q=smishing">smishing</a>
                    <a href="?q=cyber+atack">cyber atack</a>
                    <a href="?q=vr+security">vr security</a>
                    <a href="?q=malware+visulaization">malware visulaization</a>
                    <a href="?q=penetration+testing">penetration testing</a>
                    <a href="?q=courses">courses</a>
                    <a href="?q=course">course</a>
                </div>
            </div>
    """
    
    # Add spelling correction notice if applicable
    correction_notice = ""
    if was_corrected:
        correction_notice = f"""
            <div class="correction-notice">
                <strong>Spelling correction:</strong> The query "{query}" was corrected to "{corrected_query}".
            </div>
        """
    
    # Add results if we have any
    results_html = ""
    if results:
        results_json = str(results).replace("<", "&lt;").replace(">", "&gt;")
        categories_str = ", ".join(results.get('categories', []))
        total_results = results.get('total_results', 0)
        search_method = results.get('debug_info', {}).get('query_info', {}).get('method', 'unknown')
        
        # Create tabs HTML
        tab_html = """
            <div class="tab">
                <button class="tablinks active" onclick="openTab(event, 'ResultsTab')">Results</button>
                <button class="tablinks" onclick="openTab(event, 'SQLTab')">SQL Queries</button>
                <button class="tablinks" onclick="openTab(event, 'RawTab')">Raw JSON</button>
            </div>
        """
        
        # Results tab content
        results_tab = f"""
            <div id="ResultsTab" class="tabcontent active">
                <h2>Search Results</h2>
                <p>Query: <strong>"{query}"</strong></p>
                <p>Total results: <strong>{total_results}</strong></p>
                <p>Categories: <strong>{categories_str}</strong></p>
                <p>Search method: <strong>{search_method}</strong></p>
                
                <h3>Formatted Response</h3>
                <div class="formatted-response">{formatted_response}</div>
            </div>
        """
        
        # SQL queries tab content
        sql_tab = """
            <div id="SQLTab" class="tabcontent">
                <h2>SQL Queries</h2>
                <p>This shows how Django ORM translated your search into SQL queries:</p>
        """
        
        # Add SQL queries if available
        sql_queries = results.get('debug_info', {}).get('sql_queries', [])
        if sql_queries:
            for query_info in sql_queries:
                model = query_info.get('model', 'Unknown')
                orm_query = query_info.get('orm_query', 'No ORM query captured')
                sql = query_info.get('sql', 'No SQL captured')
                time_taken = query_info.get('time', 0)
                result_count = query_info.get('result_count', 0)
                
                sql_tab += f"""
                    <div class="sql-container">
                        <h3>Model: {model}</h3>
                        <div class="query-info">
                            <span class="result-count">Results: {result_count}</span>
                            <span class="time-taken">Time: {time_taken:.4f}s</span>
                        </div>
                        <div class="sql-query">{sql}</div>
                        <div class="orm-query">Django ORM: {orm_query}</div>
                    </div>
                """
        else:
            sql_tab += """
                <p>No SQL queries were captured for this search.</p>
            """
        
        sql_tab += """
            </div>
        """
        
        # Raw JSON tab content
        raw_tab = f"""
            <div id="RawTab" class="tabcontent">
                <h2>Raw Search Results</h2>
                <div class="json-display">{results_json}</div>
            </div>
        """
        
        # Combine all tabs
        results_html = tab_html + results_tab + sql_tab + raw_tab
    
    # Add the closing HTML with tab functionality
    html_end = """
        </div>
        
        <script>
            // Tab functionality
            function openTab(evt, tabName) {
                var i, tabcontent, tablinks;
                
                // Hide all tab content
                tabcontent = document.getElementsByClassName("tabcontent");
                for (i = 0; i < tabcontent.length; i++) {
                    tabcontent[i].style.display = "none";
                    tabcontent[i].classList.remove("active");
                }
                
                // Remove active class from all tab buttons
                tablinks = document.getElementsByClassName("tablinks");
                for (i = 0; i < tablinks.length; i++) {
                    tablinks[i].classList.remove("active");
                }
                
                // Show the current tab and add active class to the button
                document.getElementById(tabName).style.display = "block";
                document.getElementById(tabName).classList.add("active");
                evt.currentTarget.classList.add("active");
            }
            
            // Enable buttons in the formatted response
            document.addEventListener('DOMContentLoaded', function() {
                const formattedResponse = document.querySelector('.formatted-response');
                if (formattedResponse) {
                    const buttons = formattedResponse.querySelectorAll('.suggestion-btn');
                    buttons.forEach(button => {
                        button.addEventListener('click', function() {
                            const message = this.getAttribute('onclick').replace('sendMessage(\'', '').replace('\')', '');
                            window.location.href = '?q=' + encodeURIComponent(message);
                        });
                    });
                }
            });
        </script>
    </body>
    </html>
    """
    
    # Combine all the parts
    complete_html = html_start + search_form + correction_notice + results_html + html_end
    
    return HttpResponse(complete_html)

def format_search_results(results, query):
    """Format search results into a readable response for the chatbot"""
    response = ""
    if not results:
        return "I couldn't find any relevant information matching your query. Could you try rephrasing it or ask about something else?"

    # Check if we have a corrected query
    corrected_query = results.get('corrected_query')
    if corrected_query and corrected_query != query:
        response += f"Showing results for <em>{corrected_query}</em> instead of '{query}'.<br><br>"

    # Initialize counters for limiting results per category
    category_counts = {
        'challenges': 0,
        'courses': 0,
        'jobs': 0,
        'projects': 0,
        'articles': 0
    }
    max_per_category = 3

    # Cyber Challenges
    if 'challenges' in results and results['challenges'] and category_counts['challenges'] < max_per_category:
        response += "👋 Hi! Here are the top Cyber Challenges ready for you to tackle:<br><br>"
        response += "⸻<br><br>"
        for challenge in results['challenges'][:max_per_category]:
            if category_counts['challenges'] >= max_per_category:
                break
            difficulty_color = {
                'Easy': '🟩',
                'Medium': '🟨',
                'Hard': '🟥'
            }.get(challenge.get('difficulty', 'Medium'), '🟨')
            response += f"📘 {challenge.get('title', 'Untitled Challenge')}<br>"
            response += f"{challenge.get('description', 'No description available.')}<br>"
            response += f"{difficulty_color} Difficulty: {challenge.get('difficulty', 'Medium')}<br>"
            response += f"🔥 {challenge.get('points', 0)}<br>"
            response += f"🔗 <a href='/challenges/detail/{challenge.get('id', 0)}' class='learn-more-link'>Take Challenge</a><br><br>"
            response += "⸻<br><br>"
            category_counts['challenges'] += 1
        response += "💬 Would you like to see more cyber challenges?<br>"
        response += "<button class='suggestion-btn' onclick=\"sendMessage('Show me more cyber challenges')\">👉 Show me more cyber challenges</button><br><br>"

    # Courses
    if 'courses' in results and results['courses'] and category_counts['courses'] < max_per_category:
        response += "👋 Hi! Here are some relevant Courses you might be interested in:<br><br>"
        response += "⸻<br><br>"
        for course in results['courses'][:max_per_category]:
            if category_counts['courses'] >= max_per_category:
                break
            difficulty_color = {
                'Beginner': '🟩',
                'Intermediate': '🟨',
                'Advanced': '🟥'
            }.get(course.get('level', 'Intermediate'), '🟨')
            response += f"📚 {course.get('title', 'Untitled Course')}<br>"
            response += f"{course.get('description', 'No description available.')}<br>"
            response += f"{difficulty_color} Level: {course.get('level', 'Intermediate')}<br>"
            response += f"⏰ Duration: {course.get('duration', 'N/A')}<br>"
            response += f"🔗 <a href='/courses/detail/{course.get('id', 0)}' class='learn-more-link'>Enroll in Course</a><br><br>"
            response += "⸻<br><br>"
            category_counts['courses'] += 1
        response += "💬 Interested in more courses?<br>"
        response += "<button class='suggestion-btn' onclick=\"sendMessage('Show me more courses')\">👉 Show me more courses</button><br><br>"

    # Jobs
    if 'jobs' in results and results['jobs'] and category_counts['jobs'] < max_per_category:
        response += "👋 Hi! Here are some Job opportunities that match your interests:<br><br>"
        response += "⸻<br><br>"
        for job in results['jobs'][:max_per_category]:
            if category_counts['jobs'] >= max_per_category:
                break
            experience_color = {
                'Entry Level': '🟩',
                'Mid Level': '🟨',
                'Senior Level': '🟥'
            }.get(job.get('experience_level', 'Mid Level'), '🟨')
            response += f"💼 {job.get('title', 'Untitled Job')}<br>"
            response += f"{job.get('description', 'No description available.')}<br>"
            response += f"{experience_color} Experience: {job.get('experience_level', 'Mid Level')}<br>"
            response += f"📍 Location: {job.get('location', 'Remote')}<br>"
            response += f"🔗 <a href='/jobs/detail/{job.get('id', 0)}' class='learn-more-link'>Apply for Job</a><br><br>"
            response += "⸻<br><br>"
            category_counts['jobs'] += 1
        response += "💬 Want to explore more job opportunities?<br>"
        response += "<button class='suggestion-btn' onclick=\"sendMessage('Show me more jobs')\">👉 Show me more jobs</button><br><br>"

    # Add other categories if needed, but for now, we'll handle them generically
    for category, items in results.items():
        if category in ['challenges', 'courses', 'jobs', 'corrected_query', 'debug_info', 'total_results', 'categories']:
            continue
        if items and category_counts.get(category, 0) < max_per_category:
            response += f"👋 Hi! Here are some {category.title()} related to your query:<br><br>"
            response += "⸻<br><br>"
            for item in items[:max_per_category]:
                if category_counts.get(category, 0) >= max_per_category:
                    break
                response += f"📌 {item.get('title', f'Untitled {category}')}<br>"
                response += f"{item.get('description', 'No description available.')}<br>"
                if 'id' in item:
                    response += f"🔗 <a href='/{category}/detail/{item.get('id', 0)}' class='learn-more-link'>Learn More</a><br><br>"
                response += "⸻<br><br>"
                category_counts[category] = category_counts.get(category, 0) + 1
            response += f"💬 Want to see more {category}?<br>"
            response += f"<button class='suggestion-btn' onclick=\"sendMessage('Show me more {category}')\">👉 Show me more {category}</button><br><br>"

    return response.strip() 