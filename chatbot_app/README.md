# Hardhat Enterprises Chatbot

## Overview
This document outlines the chatbot implementation for the Hardhat Enterprises website. The chatbot is designed to provide information about the company's projects, products, services, and help users navigate the website.

## Features
- Search and retrieval system for company information
- Natural language processing for user queries
- Chat session management
- Suggested questions for easy interaction
- Links to relevant pages on the website
- FAQ database integration

## Supported Topics
The chatbot can answer questions about:
- AppAttack project
- Challenges
- Deakin Threatmirror
- Malware Visualization
- PT GUI
- Smishing Detection
- Upskilling opportunities
- VR projects
- Company information
- FAQs

## Technical Implementation
The chatbot uses a document retrieval approach that:
1. Processes user messages to extract keywords
2. Searches the database for relevant content
3. Formats and returns the most appropriate response

### Components
- **Database Models**:
  - `PageContent`: Stores content from various pages
  - `ChatSession`: Tracks chat sessions
  - `ChatMessage`: Stores individual messages
  - `FAQ`: Stores frequently asked questions
  - Other models for company information, projects, and services

- **Backend**:
  - Django views for handling chat API requests
  - Search functionality to find relevant content
  - Response formatting for natural interactions

- **Frontend**:
  - Chat interface in the website footer
  - Suggested questions for guided interactions
  - Real-time messaging with typing indicators

## Setup Instructions

### 1. Install Required Packages
Make sure you have the necessary packages installed:
```bash
pip install beautifulsoup4
```

### 2. Run Migrations
Apply the database migrations to create the necessary tables:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Populate the Database
Use the provided management command to extract content from HTML files and populate the database:
```bash
python manage.py populate_chatbot_data
```

### 4. Test the Chatbot
Start the development server and visit the website to test the chatbot:
```bash
python manage.py runserver
```

## Customization

### Adding New Content
To add new content to the chatbot's knowledge base:
1. Add new HTML pages to the appropriate directories
2. Run the `populate_chatbot_data` command again
3. Alternatively, manually add entries to the database models

### Customizing Responses
To customize how the chatbot responds:
1. Edit the `format_response` function in `views.py`
2. Modify the suggested questions in `chatbot.js`
3. Update the CSS styles in `chatbot.css`

## Future Enhancements
- Integration with AI models for more natural conversations
- User authentication to personalize responses
- Analytics to track common questions and improve responses
- Multi-language support

## Troubleshooting
- If the chatbot is not responding, check the Django console for errors
- Ensure the database is properly populated with content
- Verify that the JavaScript is loading correctly in the browser
- Check network requests for API communication issues

## REST API Endpoints

The chatbot application now provides the following REST API endpoints for interacting with the chatbot programmatically:

### 0. Connection Verification

- **URL**: `/chatbot_app/api/verify/`
- **Method**: `GET`
- **Description**: Verify that the chatbot is connected and can search the database
- **Response**: 
  ```json
  {
    "status": "success",
    "message": "Chatbot is connected and ready",
    "timestamp": "ISO timestamp"
  }
  ```
- **Error Response**:
  ```json
  {
    "status": "error",
    "message": "Error message here",
    "timestamp": "ISO timestamp"
  }
  ```

### 1. Creating a Chat Session

- **URL**: `/chatbot_app/api/sessions/`
- **Method**: `POST`
- **Description**: Creates a new chat session
- **Response**: 
  ```json
  {
    "session_id": "uuid-string",
    "created_at": "ISO timestamp",
    "status": "active"
  }
  ```

### 2. Session Details and Management

- **URL**: `/chatbot_app/api/sessions/<session_id>/`
- **Methods**: `GET`, `DELETE`
- **Description**: Get details of a chat session or deactivate it
- **GET Response**:
  ```json
  {
    "session_id": "uuid-string",
    "created_at": "ISO timestamp",
    "last_interaction": "ISO timestamp",
    "status": "active|inactive",
    "message_count": 5
  }
  ```
- **DELETE Response**:
  ```json
  {
    "status": "success",
    "message": "Session deactivated"
  }
  ```

### 3. Sending Messages and Getting Responses

- **URL**: `/chatbot_app/api/sessions/<session_id>/messages/`
- **Methods**: `POST`, `GET`
- **Description**: Send a message to the chatbot and receive a response
- **POST Request**:
  ```json
  {
    "message": "Your message text here"
  }
  ```
- **POST Response**:
  ```json
  {
    "session_id": "uuid-string",
    "message_id": 123,
    "response": "Chatbot response text",
    "timestamp": "ISO timestamp"
  }
  ```
- **GET Response** (retrieves the most recent message):
  ```json
  {
    "message_id": 123,
    "content": "Message text",
    "is_user_message": true|false,
    "timestamp": "ISO timestamp"
  }
  ```

### 4. Retrieving Chat History

- **URL**: `/chatbot_app/api/sessions/<session_id>/history/`
- **Method**: `GET`
- **Description**: Get the complete message history for a session
- **Response**:
  ```json
  {
    "session_id": "uuid-string",
    "message_count": 10,
    "created_at": "ISO timestamp",
    "last_interaction": "ISO timestamp",
    "status": "active|inactive",
    "messages": [
      {
        "message_id": 1,
        "content": "Message text",
        "is_user_message": true|false,
        "timestamp": "ISO timestamp"
      },
      // More messages...
    ]
  }
  ```

## Example Usage

### JavaScript/Fetch API Example

```javascript
// Create a new chat session
async function createSession() {
  const response = await fetch('/chatbot_app/api/sessions/', {
    method: 'POST'
  });
  const data = await response.json();
  return data.session_id;
}

// Send a message to the chatbot
async function sendMessage(sessionId, message) {
  const response = await fetch(`/chatbot_app/api/sessions/${sessionId}/messages/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message })
  });
  return await response.json();
}

// Get chat history
async function getChatHistory(sessionId) {
  const response = await fetch(`/chatbot_app/api/sessions/${sessionId}/history/`);
  return await response.json();
}

// Example usage
async function chatExample() {
  const sessionId = await createSession();
  
  // Send a message and get response
  const response = await sendMessage(sessionId, "Tell me about AppAttack");
  console.log(response.response);
  
  // Get the chat history
  const history = await getChatHistory(sessionId);
  console.log(history.messages);
} 
```

## Enhanced Search Capabilities

The chatbot now has expanded search capabilities, including access to a wide range of content from the website database. The search engine can now query the following types of information:

### Available Content Types

- **Projects**: Information about all Hardhat projects, including AppAttack, DeakinThreatmirror, and more
- **Courses**: Educational offerings and training programs
- **Skills**: Cybersecurity and technical skills information
- **Jobs**: Current job openings and career opportunities
- **Articles**: Blog posts and informational articles
- **Announcements**: Latest news and important updates
- **Challenges**: Cybersecurity challenges with varying difficulty levels
- **FAQs**: Frequently asked questions and their answers
- **Experiences**: User testimonials and feedback
- **Page Content**: General content from website pages
- **Contact Information**: Ways to get in touch with Hardhat
- **Join Requests**: Information about how to join projects

### Security and Privacy Considerations

The search engine has been designed with security in mind:
- **Excluded Fields**: Sensitive information fields like "answer", "explanation", "password", "secret", "token", and "api_key" are excluded from general searches
- **User Data Protection**: User and Student models are entirely excluded from search results
- **Sanitized Input**: All user queries are preprocessed and sanitized
- **Restricted Access**: Certain data is only accessible when explicitly requested

### Sample Queries

Users can now ask the chatbot about a broader range of topics:

- "Tell me about available projects"
- "What courses do you offer?"
- "Are there any job openings?"
- "Show me cybersecurity challenges"
- "What skills can I learn?"
- "Any recent announcements?"
- "How can I contact Hardhat?"
- "How do I join a project?"

## API Security

The chatbot API endpoints now include several security enhancements to protect against common vulnerabilities:

### 1. Signature-Based Authentication

All API requests must include a valid signature to prevent tampering and unauthorized access. The authentication mechanism works as follows:

1. When a session is created, the server returns a timestamp and signature
2. For subsequent requests, the client must:
   - Include the session ID in the URL
   - Send a current timestamp in the `X-Timestamp` header
   - Generate and send a signature in the `X-Signature` header

The signature is generated using:

```javascript
// JavaScript example
function generateSignature(sessionId, timestamp, secretKey) {
  // In a real client, you would need to securely store or obtain the secretKey
  const message = `${sessionId}:${timestamp}:${secretKey}`;
  // Use a cryptographic hash function (like SHA-256)
  return sha256(message);
}
```

### 2. Input Validation and Sanitization

- All user input is validated for length and format
- Message content is sanitized to prevent XSS attacks
- JSON payloads are validated before processing

### 3. Rate Limiting and Abuse Prevention

- Client IP addresses are logged for security monitoring
- Request timestamps are validated to prevent replay attacks
- Message size is limited to 1000 characters

### 4. Error Handling and Logging

- Comprehensive error logging for security monitoring
- Structured error responses that don't leak sensitive information
- Graceful handling of invalid requests

### 5. Additional Protections

- `never_cache` decorators to prevent response caching
- CSRF protection for authenticated endpoints
- Secure session handling with proper timeout

### Client Implementation Example

```javascript
// Create a session
async function createSession() {
  const response = await fetch('/chatbot_app/api/sessions/', {
    method: 'POST'
  });
  const data = await response.json();
  
  // Store session details from response
  const sessionId = data.session_id;
  const timestamp = response.headers.get('X-Timestamp');
  const signature = response.headers.get('X-Signature');
  
  return { sessionId, timestamp, signature };
}

// Send an authenticated message
async function sendMessage(sessionId, message) {
  // Generate new timestamp for each request
  const timestamp = Math.floor(Date.now() / 1000).toString();
  
  // Generate signature using your secret key
  const signature = generateSignature(sessionId, timestamp, SECRET_KEY);
  
  const response = await fetch(`/chatbot_app/api/sessions/${sessionId}/messages/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Timestamp': timestamp,
      'X-Signature': signature
    },
    body: JSON.stringify({ message })
  });
  
  return await response.json();
}
```

## Testing

### Connection Verification Tests

The chatbot includes comprehensive tests to verify its connection status:

1. **Endpoint Verification**
   - Tests the `/chatbot_app/api/verify/` endpoint
   - Verifies response structure and status codes
   - Logs connection status and any errors

2. **Search Engine Connection**
   - Tests the `verify_search_connection` function
   - Verifies database connectivity
   - Logs search engine status

3. **Database Operations**
   - Tests creation of chat sessions and messages
   - Verifies database connectivity
   - Logs successful operations

4. **Error Handling**
   - Tests error scenarios
   - Verifies proper error responses
   - Logs error conditions

Test results are logged to `chatbot_app/tests/test_results.log` for monitoring and debugging.

To run the connection tests:
```bash
python manage.py test chatbot_app.tests.test_connection
```