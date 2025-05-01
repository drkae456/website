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
    
    // Initialize chat functionality if we're on the chat page
    if (document.querySelector('.chat-container')) {
        initChat();
    }
});

// Chat functionality
function initChat() {
    // Session management
    let sessionId = localStorage.getItem('chatSessionId') || null;
    
    // DOM elements
    const chatBox = document.getElementById('chat-box');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const connectionStatus = document.getElementById('connection-status');
    
    // Initialize chat
    function initializeChat() {
        // Show connection status
        connectionStatus.innerText = 'Connected to Hardie Hat';
        connectionStatus.classList.remove('connecting');
        connectionStatus.classList.add('connected');
        
        // Add welcome message
        addBotMessage("Hello! Welcome to Hardhat Enterprises. My name is Hardie Hat. I am here to help you explore the world of Hardhat Enterprises.");
        
        // Add suggested questions
        addSuggestedQuestions();
    }
    
    // Add a message to the chat box
    function addMessage(message, isBot = true) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message');
        messageElement.classList.add(isBot ? 'bot-message' : 'user-message');
        messageElement.innerHTML = message;
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
    
    // Add a bot message
    function addBotMessage(message) {
        addMessage(message, true);
    }
    
    // Add a user message
    function addUserMessage(message) {
        addMessage(message, false);
    }
    
    // Show typing indicator
    function showTypingIndicator() {
        const typingIndicator = document.createElement('div');
        typingIndicator.classList.add('typing-indicator');
        typingIndicator.id = 'typing-indicator';
        typingIndicator.innerHTML = '<span></span><span></span><span></span>';
        chatBox.appendChild(typingIndicator);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
    
    // Hide typing indicator
    function hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // Add suggested questions
    function addSuggestedQuestions() {
        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.classList.add('suggested-questions');
        suggestionsDiv.innerHTML = `
            <p>Here are some things you can ask:</p>
            <button class="suggestion-btn" onclick="sendMessage('What is AppAttack?')">What is AppAttack?</button>
            <button class="suggestion-btn" onclick="sendMessage('Tell me about VR Security')">Tell me about VR Security</button>
            <button class="suggestion-btn" onclick="sendMessage('What projects do you have?')">What projects do you have?</button>
            <button class="suggestion-btn" onclick="sendMessage('How can I join?')">How can I join?</button>
        `;
        chatBox.appendChild(suggestionsDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
    
    // Send a message
    function sendMessage(message = null) {
        // Get message from input or parameter
        const messageText = message || messageInput.value.trim();
        
        // Don't send empty messages
        if (!messageText) return;
        
        // Add user message to chat
        addUserMessage(messageText);
        
        // Clear input if using the input field
        if (!message) {
            messageInput.value = '';
        }
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send message to server
        fetch('/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: messageText,
                session_id: sessionId,
                user_info: {
                    is_authenticated: false,
                    username: 'Guest'
                }
            })
        })
        .then(response => response.json())
        .then(data => {
            // Hide typing indicator
            hideTypingIndicator();
            
            // Store session ID if provided
            if (data.session_id) {
                sessionId = data.session_id;
                localStorage.setItem('chatSessionId', sessionId);
            }
            
            // Add bot response with delay
            setTimeout(() => {
                addBotMessage(data.response);
            }, data.typing_delay || 500);
        })
        .catch(error => {
            // Hide typing indicator
            hideTypingIndicator();
            
            // Show error message
            addBotMessage("Sorry, I'm having trouble connecting. Please try again later.");
            console.error('Error:', error);
            
            // Update connection status
            connectionStatus.innerText = 'Connection error. Please try again.';
            connectionStatus.classList.remove('connecting', 'connected');
            connectionStatus.classList.add('error');
        });
    }
    
    // Event listeners
    sendButton.addEventListener('click', () => sendMessage());
    
    messageInput.addEventListener('keypress', event => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });
    
    // Make sendMessage available globally
    window.sendMessage = sendMessage;
    
    // Initialize the chat
    initializeChat();
} 