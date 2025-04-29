import requests
import json
import time
import hashlib
from pprint import pprint

# Configuration
MAIN_SERVER_URL = 'http://127.0.0.1:8000'
CHATBOT_SERVER_URL = 'http://127.0.0.1:5005'
USERNAME = input("Enter your username: ")
PASSWORD = input("Enter your password: ")
SESSION = requests.Session()

def login():
    """Login to the main application and return session cookies"""
    # Get CSRF token first
    response = SESSION.get(f"{MAIN_SERVER_URL}/accounts/login/")
    if response.status_code != 200:
        print(f"Failed to get login page: {response.status_code}")
        return False
    
    # Extract CSRF token (assuming it's in the cookies)
    csrf_token = SESSION.cookies.get('csrftoken')
    
    # Now attempt login
    login_data = {
        'username': USERNAME,
        'password': PASSWORD,
        'csrfmiddlewaretoken': csrf_token
    }
    
    headers = {
        'Referer': f"{MAIN_SERVER_URL}/accounts/login/",
        'X-CSRFToken': csrf_token
    }
    
    response = SESSION.post(
        f"{MAIN_SERVER_URL}/accounts/login/", 
        data=login_data,
        headers=headers
    )
    
    # Check if login was successful (302 redirect is typical)
    if response.status_code == 200 and "Login failed" in response.text:
        print("Login failed. Check your credentials.")
        return False
    
    print(f"Login response status: {response.status_code}")
    
    # Save cookies to session
    return True

def get_user_info():
    """Get current user info from main application"""
    response = SESSION.get(
        f"{MAIN_SERVER_URL}/get-current-user/",
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code != 200:
        print(f"Failed to get user info: {response.status_code}")
        return None
    
    return response.json()

def create_chatbot_session():
    """Create a new chatbot session"""
    response = SESSION.post(
        f"{CHATBOT_SERVER_URL}/chatbot/api/sessions/",
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    )
    
    if response.status_code != 201:
        print(f"Failed to create chatbot session: {response.status_code}")
        return None
    
    return response.json().get('session_id')

def send_chatbot_message(session_id, message, user_info):
    """Send a message to the chatbot with authentication data"""
    # Create payload with auth token
    payload = {
        'message': message,
        'session_id': session_id,
        'user_info': {
            'is_authenticated': user_info.get('is_authenticated', False),
            'user_id': user_info.get('id'),
            'username': user_info.get('first_name', 'Guest'),
            'email': user_info.get('email', ''),
            'auth_token': user_info.get('auth_token', ''),
            'auth_timestamp': user_info.get('auth_timestamp', '')
        }
    }
    
    # Send request to chatbot
    response = SESSION.post(
        f"{CHATBOT_SERVER_URL}/chatbot/chat/",
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Auth-Token': user_info.get('auth_token', ''),
            'X-Auth-Timestamp': user_info.get('auth_timestamp', '')
        },
        json=payload
    )
    
    if response.status_code != 200:
        print(f"Failed to send message: {response.status_code}")
        return None
    
    return response.json()

def check_authentication_after_chatbot():
    """Check if user is still authenticated after chatbot interaction"""
    response = SESSION.get(
        f"{MAIN_SERVER_URL}/get-current-user/",
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code != 200:
        print(f"Failed to check authentication: {response.status_code}")
        return None
    
    return response.json()

def main():
    print("=== Authentication Test ===")
    
    # Step 1: Login to main application
    print("\n1. Logging in to main application...")
    if not login():
        print("Login failed. Exiting.")
        return
    
    # Step 2: Get user info (with auth token)
    print("\n2. Getting user info...")
    user_info = get_user_info()
    if not user_info:
        print("Failed to get user info. Exiting.")
        return
    
    print(f"Authenticated as: {user_info.get('first_name')} (ID: {user_info.get('id')})")
    print(f"Auth token: {user_info.get('auth_token', 'None')}")
    print(f"Auth timestamp: {user_info.get('auth_timestamp', 'None')}")
    
    # Step 3: Create chatbot session
    print("\n3. Creating chatbot session...")
    session_id = create_chatbot_session()
    if not session_id:
        print("Failed to create chatbot session. Exiting.")
        return
    
    print(f"Chatbot session created: {session_id}")
    
    # Step 4: Send message to chatbot
    print("\n4. Sending message to chatbot...")
    test_message = "Tell me about AppAttack"
    response = send_chatbot_message(session_id, test_message, user_info)
    if not response:
        print("Failed to send message to chatbot. Exiting.")
        return
    
    print("Message sent successfully!")
    print(f"Response starts with: {response.get('response', '')[:100]}...")
    
    # Step 5: Check if still authenticated
    print("\n5. Checking if still authenticated...")
    time.sleep(1)  # Small delay to ensure any session changes take effect
    new_user_info = check_authentication_after_chatbot()
    
    if not new_user_info:
        print("Failed to check authentication status. Exiting.")
        return
    
    print(f"Is authenticated: {new_user_info.get('is_authenticated', False)}")
    print(f"Username: {new_user_info.get('first_name', 'Unknown')}")
    
    # Step 6: Verify token consistency
    print("\n6. Verifying authentication token consistency...")
    if user_info.get('auth_token') != new_user_info.get('auth_token'):
        print("WARNING: Auth token changed after chatbot interaction!")
        print(f"Old token: {user_info.get('auth_token')}")
        print(f"New token: {new_user_info.get('auth_token')}")
    else:
        print("Auth token remained consistent")
    
    # Step 7: Summary
    print("\n=== TEST SUMMARY ===")
    print(f"Initial authentication: {user_info.get('is_authenticated', False)}")
    print(f"After chatbot: {new_user_info.get('is_authenticated', False)}")
    print(f"Authentication maintained: {new_user_info.get('is_authenticated') == user_info.get('is_authenticated')}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main() 