// Global variables
let currentUser = { isLoggedIn: false, name: 'Guest' };
let chatHistory = []; // Array to hold message objects { sender: 'user'/'bot', text: 'message', timestamp: number }
let messageInput;
let chatBox;
let sessionId;
let connectionStatus;
let isResizing = false;

// Update the chatbot server URL to use separate port
const CHATBOT_SERVER_URL = 'http://127.0.0.1:8000/chatbot';

// Function to ensure chat scrolls to bottom
function scrollChatToBottom() {
    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

// Core Functions
function addMessage(messageObject, isLoadingHistory = false) {
    if (!chatBox) {
        chatBox = document.getElementById("chat-box");
    }
    if (!chatBox) {
        console.error("Chat box not found, cannot add message.");
        return;
    }
    const messageDiv = document.createElement('div');
    const isUser = messageObject.sender === 'user';
    const isBot = messageObject.sender === 'bot';
    const isIndicator = messageObject.sender === 'indicator';

    messageDiv.className = `message ${isUser ? 'user-message' : isBot ? 'bot-message' : 'typing-indicator'}`;

    let prefix = '';
    if (isUser) {
        prefix = `${currentUser.isLoggedIn ? currentUser.name : 'Guest'}: `;
        messageDiv.textContent = prefix + messageObject.text;
    } else if (isBot) {
        // Use a span with a specific class for the bot prefix so we can style and identify it
        prefix = '<span class="bot-prefix">Hardhat Assistant:</span> ';
        let formattedMessage = messageObject.text || "";
        formattedMessage = formattedMessage.replace(/\\n/g, '<br>');
        const pathRegex = /(\/[\\w\/-]+)/g;
        formattedMessage = formattedMessage.replace(pathRegex, '<a href="$1" target="_blank">$1</a>');
        messageDiv.innerHTML = prefix + formattedMessage;
    } else if (isIndicator) {
        messageDiv.id = 'typing-indicator';
        messageDiv.textContent = messageObject.text;
    }

    chatBox.appendChild(messageDiv);

    if ((isUser || isBot) && !isLoadingHistory) {
        messageObject.timestamp = messageObject.timestamp || Date.now();
        chatHistory.push(messageObject);
        saveChatHistory();
    }

    // Adjust scroll behavior based on the message type
    if (isBot) {
        // For bot messages, scroll to show the start of the message
        scrollToMessageStart(messageDiv);
    } else {
        // For user messages and typing indicators, scroll to bottom
        scrollChatToBottom();
    }
}

// Function to ensure bot response always appears at the top of the viewport
function scrollToMessageStart(messageElement) {
    if (!chatBox || !messageElement) return;
    
    // Ensure the bot prefix is properly styled
    if (messageElement.classList.contains('bot-message')) {
        const botPrefix = messageElement.querySelector('.bot-prefix');
        
        // If there's no prefix already highlighted, add it
        if (!botPrefix) {
            const messageText = messageElement.innerHTML;
            const prefixedMessage = messageText.replace(
                'Hardhat Assistant:', 
                '<span class="bot-prefix">Hardhat Assistant:</span>'
            );
            messageElement.innerHTML = prefixedMessage;
        }
    }
    
    // CRITICAL CHANGE: Get the exact position of the message element
    const messageRect = messageElement.getBoundingClientRect();
    const chatBoxRect = chatBox.getBoundingClientRect();
    
    // Calculate the precise scroll position to show the message at the top
    // We need to account for the relative position of the message within the chatbox
    const messageRelativeTop = messageElement.offsetTop;
    
    // Force scroll to exactly the top of the message with no offset
    chatBox.scrollTop = messageRelativeTop;
    
    console.log("Scrolled to show message at top:", {
        messageTop: messageRelativeTop,
        newScrollTop: chatBox.scrollTop
    });
    
    // Add a highlight class to the message to draw attention to it
    messageElement.classList.add('highlight-message');
    
    // Remove the highlight after a short delay
    setTimeout(() => {
        messageElement.classList.remove('highlight-message');
        
        // Double-check scroll position after a short delay
        chatBox.scrollTop = messageRelativeTop;
    }, 1000);
    
    // Set another timeout to ensure scroll position is maintained
    setTimeout(() => {
        chatBox.scrollTop = messageRelativeTop;
    }, 500);
}

function saveChatHistory() {
    try {
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
    } catch (e) {
        console.error("Error saving chat history:", e);
    }
}

function addTypingIndicator() {
    removeTypingIndicator();
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message typing-indicator';
    messageDiv.id = 'typing-indicator';
    
    // Create the animated typing indicator with dots
    const typingContent = document.createElement('div');
    typingContent.className = 'typing-content';
    typingContent.innerHTML = 'Hardhat Assistant is typing<span class="dot-1">.</span><span class="dot-2">.</span><span class="dot-3">.</span>';
    
    messageDiv.appendChild(typingContent);
    
    if (!chatBox) {
        chatBox = document.getElementById("chat-box");
    }
    
    if (chatBox) {
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
    
    // Start the blinking animation for dots
    startTypingAnimation();
}

function startTypingAnimation() {
    const animateDots = () => {
        const dot1 = document.querySelector('.dot-1');
        const dot2 = document.querySelector('.dot-2');
        const dot3 = document.querySelector('.dot-3');
        
        if (!dot1 || !dot2 || !dot3) return;
        
        // Animation sequence
        setTimeout(() => {
            dot1.style.opacity = '1';
        }, 200);
        
        setTimeout(() => {
            dot2.style.opacity = '1';
        }, 400);
        
        setTimeout(() => {
            dot3.style.opacity = '1';
        }, 600);
        
        setTimeout(() => {
            dot1.style.opacity = '0.2';
            dot2.style.opacity = '0.2';
            dot3.style.opacity = '0.2';
        }, 900);
    };
    
    // Run the animation immediately and then every second
    animateDots();
    window.typingAnimationInterval = setInterval(animateDots, 1000);
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
    
    // Clear the animation interval
    if (window.typingAnimationInterval) {
        clearInterval(window.typingAnimationInterval);
        window.typingAnimationInterval = null;
    }
}

async function getUserInfo() {
    try {
        const response = await fetch('/get-current-user/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include'
        });
        const data = await response.json();
        return {
            isLoggedIn: data.is_authenticated,
            name: data.first_name || 'User',
            id: data.id,
            email: data.email,
            authToken: data.auth_token,
            authTimestamp: data.auth_timestamp
        };
    } catch (error) {
        console.error('Error fetching user info:', error);
        return { isLoggedIn: false, name: 'Guest' };
    }
}

// Chat Functions
async function sendMessage(directMessage = null) {
    if (!messageInput) {
        messageInput = document.getElementById("message-input");
    }
    
    const messageText = directMessage || (messageInput ? messageInput.value.trim() : '');
    
    if (messageText) {
        const userInfo = await getUserInfo();
        currentUser = userInfo;
        
        const userMessage = {
            sender: 'user',
            text: messageText,
            timestamp: Date.now()
        };
        addMessage(userMessage);
        
        if (!directMessage && messageInput) {
            messageInput.value = '';
        }
        
        addTypingIndicator();
        
        let curSessionId = sessionId || localStorage.getItem('chatSessionId');
        
        if (!curSessionId) {
            const newSessionId = await createNewSession();
            if (newSessionId) {
                curSessionId = newSessionId;
                await sendMessageToServer(messageText, curSessionId);
            } else {
                handleSendError("Could not create a chat session");
            }
        } else {
            await sendMessageToServer(messageText, curSessionId);
        }
    }
}

// Function to scroll to specific message by selector
function scrollToSpecificMessage(selector) {
    const specificMessage = document.querySelector(selector);
    if (specificMessage && specificMessage.classList.contains('bot-message')) {
        console.log("Found specific message:", specificMessage);
        
        // Get the position of the specific message
        const messageTop = specificMessage.offsetTop;
        
        // Force scroll to exactly the top position
        chatBox.scrollTop = messageTop;
        
        // Add a highlight effect
        specificMessage.classList.add('highlight-message');
        setTimeout(() => {
            specificMessage.classList.remove('highlight-message');
        }, 1500);
        
        return true;
    }
    return false;
}

// Add a utility function to scroll to the message at 6th position if it exists
function scrollToSixthMessage() {
    scrollToSpecificMessage("#chat-box > div:nth-child(6)");
}

// Modify sendMessageToServer to include the specific message check
async function sendMessageToServer(messageText, curSessionId) {
    try {
        // Get the latest user info before sending
        const userInfo = await getUserInfo();
        
        // Get CSRF token from cookie
        const csrfToken = getCookie('csrftoken');
        
        const response = await fetch(`${CHATBOT_SERVER_URL}/chat/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-CSRFToken': csrfToken || '',
                'X-Auth-Token': userInfo.authToken || '',
                'X-Auth-Timestamp': userInfo.authTimestamp || ''
            },
            mode: 'cors',
            credentials: 'include',
            body: JSON.stringify({
                message: messageText,
                session_id: curSessionId,
                user_info: {
                    is_authenticated: userInfo.isLoggedIn,
                    user_id: userInfo.id,
                    username: userInfo.name,
                    email: userInfo.email,
                    auth_token: userInfo.authToken,
                    auth_timestamp: userInfo.authTimestamp
                }
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Check if we have a typing delay from the server
        const typingDelay = data.typing_delay || 0;
        
        if (typingDelay > 0) {
            // Keep the typing indicator visible for the specified delay
            await new Promise(resolve => setTimeout(resolve, typingDelay));
        }
        
        removeTypingIndicator();
        
        const botResponse = {
            sender: 'bot',
            text: data.response || "Sorry, I couldn't process that.",
            timestamp: Date.now()
        };
        
        // Add the bot's message to the chat
        addMessage(botResponse);
        
        // CRITICAL FIX: Immediately find and scroll to the just-added bot message
        setTimeout(() => {
            const allBotMessages = chatBox.querySelectorAll('.bot-message');
            if (allBotMessages.length > 0) {
                // Get the last (most recent) bot message
                const latestBotMessage = allBotMessages[allBotMessages.length - 1];
                
                // Force scroll to this message
                const messageTop = latestBotMessage.offsetTop;
                chatBox.scrollTop = messageTop;
                
                console.log("Immediate scroll to latest bot message at position:", messageTop);
                
                // Check for the specific 6th message as well
                scrollToSixthMessage();
            }
        }, 10);
        
        // Add another check after a slightly longer delay
        setTimeout(() => {
            const allBotMessages = chatBox.querySelectorAll('.bot-message');
            if (allBotMessages.length > 0) {
                const latestBotMessage = allBotMessages[allBotMessages.length - 1];
                const messageTop = latestBotMessage.offsetTop;
                chatBox.scrollTop = messageTop;
            }
        }, 100);
        
    } catch (error) {
        handleSendError(error.message);
    }
}

// Helper function to get cookie value
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function handleSendError(errorMessage) {
    removeTypingIndicator();
    console.error('Error sending message:', errorMessage);
    
    const botErrorMessage = {
        sender: 'bot',
        text: "Sorry, I'm having trouble connecting. Please try again later.",
        timestamp: Date.now()
    };
    addMessage(botErrorMessage);
    checkChatbotConnection();
}

// Connection Functions
async function checkChatbotConnection() {
    connectionStatus.textContent = "Connecting to Hardhat Assistant...";
    connectionStatus.classList.remove('connected', 'disconnected');
    connectionStatus.classList.add('connecting');
    
    try {
        const response = await fetch(`${CHATBOT_SERVER_URL}/api/verify/`, {
            method: 'GET',
            credentials: 'include',
            mode: 'cors',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            connectionStatus.textContent = "You have been connected to Hardhat Assistant";
            connectionStatus.classList.remove('connecting');
            connectionStatus.classList.add('connected');
            
            if (!localStorage.getItem('chatSessionId')) {
                await createNewSession();
            }
            
            return true;
        } else if (data.status === 'partial') {
            connectionStatus.textContent = "Connected with limited functionality. Some features may not work.";
            connectionStatus.classList.remove('connecting');
            connectionStatus.classList.add('connected');
            console.warn("Chatbot connected with partial functionality:", data.message, data.diagnostics);
            
            if (!localStorage.getItem('chatSessionId')) {
                await createNewSession();
            }
            
            return true;
        } else {
            connectionStatus.textContent = "Unable to connect to Hardhat Assistant: " + data.message;
            connectionStatus.classList.remove('connecting');
            connectionStatus.classList.add('disconnected');
            console.error("Chatbot connection error:", data);
            return false;
        }
    } catch (error) {
        connectionStatus.textContent = "Error connecting to Hardhat Assistant. Is the chatbot server running?";
        connectionStatus.classList.remove('connecting');
        connectionStatus.classList.add('disconnected');
        console.error("Chatbot connection error:", error);
        return false;
    }
}

async function createNewSession() {
    try {
        const response = await fetch(`${CHATBOT_SERVER_URL}/api/sessions/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors',
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            sessionId = data.session_id;
            localStorage.setItem('chatSessionId', sessionId);
            console.log("Created new chat session:", sessionId);
            return sessionId;
        } else {
            console.error("Failed to create new session:", response.status, response.statusText);
            return null;
        }
    } catch (error) {
        console.error("Error creating new chat session:", error);
        return null;
    }
}

// UI Functions
function toggleFullscreen() {
    // Do nothing - fullscreen mode has been removed
    console.log("Fullscreen mode has been disabled");
    return false;
}

// Resize Functions
function initResizableChatbox() {
    const chatPopup = document.getElementById("chat-popup");
    if (!chatPopup) return;
    
    // Create side resize handles ONLY for left and top
    const handleNames = ['left', 'top'];
    handleNames.forEach(side => {
        const sideHandle = document.createElement('div');
        sideHandle.className = `resize-handle-${side}`;
        chatPopup.appendChild(sideHandle);
    });
    
    // Initialize side resize functionality for left and top only
    setupSideResize(chatPopup);
    
    // Store initial dimensions in local storage if not already there
    if (!localStorage.getItem('chatbot-width')) {
        localStorage.setItem('chatbot-width', '350px');
    }
    if (!localStorage.getItem('chatbot-height')) {
        localStorage.setItem('chatbot-height', '500px');
    }
    if (!localStorage.getItem('chatbot-left')) {
        localStorage.setItem('chatbot-left', '20px');
    }
    if (!localStorage.getItem('chatbot-bottom')) {
        localStorage.setItem('chatbot-bottom', '20px');
    }
    
    // Apply stored dimensions
    const storedWidth = localStorage.getItem('chatbot-width');
    const storedHeight = localStorage.getItem('chatbot-height');
    const storedLeft = localStorage.getItem('chatbot-left');
    const storedBottom = localStorage.getItem('chatbot-bottom');
    const storedTop = localStorage.getItem('chatbot-top');
    
    if (storedWidth && storedHeight) {
        chatPopup.style.width = storedWidth;
        chatPopup.style.height = storedHeight;
    }
    
    if (storedLeft) {
        chatPopup.style.right = 'auto';
        chatPopup.style.left = storedLeft;
    }
    
    // If top position is stored, use that instead of bottom position
    if (storedTop) {
        chatPopup.style.top = storedTop;
        chatPopup.style.bottom = 'auto';
    } else if (storedBottom) {
        chatPopup.style.bottom = storedBottom;
        chatPopup.style.top = 'auto';
    }
    
    // Ensure chat scrolls to bottom after applying dimensions
    setTimeout(scrollChatToBottom, 100);
}

// Function to setup side resize functionality (now only for left and top)
function setupSideResize(chatPopup) {
    const leftHandle = chatPopup.querySelector('.resize-handle-left');
    const topHandle = chatPopup.querySelector('.resize-handle-top');
    
    if (leftHandle) setupLeftResize(chatPopup, leftHandle);
    if (topHandle) setupTopResize(chatPopup, topHandle);
}

// Left side resize
function setupLeftResize(chatPopup, handle) {
    let startX, startWidth;
    
    const startResize = (e) => {
        e.preventDefault();
        chatPopup.classList.add('resizing');
        
        startX = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
        startWidth = parseInt(document.defaultView.getComputedStyle(chatPopup).width, 10);
        
        document.addEventListener('mousemove', resize);
        document.addEventListener('touchmove', resize, { passive: false });
        document.addEventListener('mouseup', stopResize);
        document.addEventListener('touchend', stopResize);
    };
    
    const resize = (e) => {
        if (e.type === 'touchmove') e.preventDefault();
        
        // Only apply if not in fullscreen
        if (!chatPopup.classList.contains('fullscreen-chat')) {
            const clientX = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
            const dx = clientX - startX;
            const newWidth = startWidth - dx;
            
            const minWidth = 300;
            const maxWidth = window.innerWidth * 0.8;
            
            if (newWidth >= minWidth && newWidth <= maxWidth) {
                chatPopup.style.width = `${newWidth}px`;
                // Keep position fixed at bottom right
                chatPopup.style.right = "20px";
                chatPopup.style.bottom = "20px";
                chatPopup.style.left = "auto";
                
                localStorage.setItem('chatbot-width', chatPopup.style.width);
            }
        }
        
        scrollChatToBottom();
    };
    
    const stopResize = () => {
        chatPopup.classList.remove('resizing');
        document.removeEventListener('mousemove', resize);
        document.removeEventListener('touchmove', resize);
        document.removeEventListener('mouseup', stopResize);
        document.removeEventListener('touchend', stopResize);
        setTimeout(scrollChatToBottom, 50);
    };
    
    handle.addEventListener('mousedown', startResize);
    handle.addEventListener('touchstart', startResize, { passive: false });
}

// Top side resize - modified to keep position fixed
function setupTopResize(chatPopup, handle) {
    let startY, startHeight;
    
    const startResize = (e) => {
        e.preventDefault();
        chatPopup.classList.add('resizing');
        
        startY = e.clientY || (e.touches && e.touches[0] ? e.touches[0].clientY : 0);
        startHeight = parseInt(document.defaultView.getComputedStyle(chatPopup).height, 10);
        
        document.addEventListener('mousemove', resize);
        document.addEventListener('touchmove', resize, { passive: false });
        document.addEventListener('mouseup', stopResize);
        document.addEventListener('touchend', stopResize);
    };
    
    const resize = (e) => {
        if (e.type === 'touchmove') e.preventDefault();
        
        // Only apply if not in fullscreen
        if (!chatPopup.classList.contains('fullscreen-chat')) {
            const clientY = e.clientY || (e.touches && e.touches[0] ? e.touches[0].clientY : 0);
            const dy = clientY - startY;
            const newHeight = startHeight - dy;
            
            const minHeight = 400;
            const maxHeight = window.innerHeight * 0.9;
            
            if (newHeight >= minHeight && newHeight <= maxHeight) {
                chatPopup.style.height = `${newHeight}px`;
                // Keep position fixed at bottom right
                chatPopup.style.right = "20px";
                chatPopup.style.bottom = "20px";
                chatPopup.style.top = "auto";
                
                localStorage.setItem('chatbot-height', chatPopup.style.height);
            }
        }
        
        scrollChatToBottom();
    };
    
    const stopResize = () => {
        chatPopup.classList.remove('resizing');
        document.removeEventListener('mousemove', resize);
        document.removeEventListener('touchmove', resize);
        document.removeEventListener('mouseup', stopResize);
        document.removeEventListener('touchend', stopResize);
        setTimeout(scrollChatToBottom, 50);
    };
    
    handle.addEventListener('mousedown', startResize);
    handle.addEventListener('touchstart', startResize, { passive: false });
}

function loadChatHistory() {
    if (!chatBox) return [];
    
    const savedHistory = localStorage.getItem('chatHistory');
    if (savedHistory) {
        try {
            const parsedHistory = JSON.parse(savedHistory);
            chatBox.innerHTML = '';
            
            // First load all messages 
            parsedHistory.forEach(msg => addMessage(msg, true));
            
            // Then ensure bot messages have the proper prefix styling
            const botMessages = chatBox.querySelectorAll('.bot-message');
            botMessages.forEach(msg => {
                if (!msg.querySelector('.bot-prefix')) {
                    const messageText = msg.innerHTML;
                    const prefixedMessage = messageText.replace(
                        'Hardhat Assistant:', 
                        '<span class="bot-prefix">Hardhat Assistant:</span>'
                    );
                    msg.innerHTML = prefixedMessage;
                }
            });
            
            // Scroll to the first bot message if any exists
            if (botMessages.length > 0) {
                scrollToMessageStart(botMessages[0]);
            }
            
            return parsedHistory;
        } catch (e) {
            console.error("Error parsing chat history:", e);
            localStorage.removeItem('chatHistory');
            return [];
        }
    }
    return [];
}

function addSuggestedQuestions() {
    if (!chatBox) return;
    if (chatBox.querySelector('.suggested-questions')) {
        return;
    }

    const suggestionsDiv = document.createElement('div');
    suggestionsDiv.className = 'suggested-questions';
    suggestionsDiv.innerHTML = `
        <p>Here are some things you can ask me about:</p>
        <button class="suggestion-btn" onclick="sendMessage('Tell me about AppAttack')">Tell me about AppAttack</button>
        <button class="suggestion-btn" onclick="sendMessage('What challenges are available?')">What challenges are available?</button>
        <button class="suggestion-btn" onclick="sendMessage('What is Deakin Threatmirror?')">What is Deakin Threatmirror?</button>
        <button class="suggestion-btn" onclick="sendMessage('Tell me about malware visualization')">Tell me about malware visualization</button>
        <button class="suggestion-btn" onclick="sendMessage('What is PT GUI?')">What is PT GUI?</button>
        <button class="suggestion-btn" onclick="sendMessage('What is smishing detection?')">What is smishing detection?</button>
        <button class="suggestion-btn" onclick="sendMessage('How can I upskill?')">How can I upskill?</button>
        <button class="suggestion-btn" onclick="sendMessage('Tell me about VR projects')">Tell me about VR projects</button>
    `;
    chatBox.appendChild(suggestionsDiv);
    
    // We don't force scrolling here, as we want to preserve the scrolling position
    // This allows viewing the start of messages even when suggestions are added
}

async function initializeChat() {
    if (!chatBox) {
        console.error("Chat box not found during initialization.");
        return;
    }
    
    chatHistory = [];
    
    const userInfo = await getUserInfo();
    currentUser = userInfo;
    
    const welcomeMessage = {
        sender: 'bot',
        text: "Hello! Welcome to Hardhat Enterprises. I'm your Hardhat Assistant, here to help you explore our products and services.",
        timestamp: Date.now()
    };
    
    // Clear any existing content
    chatBox.innerHTML = '';
    
    // Add the welcome message
    addMessage(welcomeMessage);
    
    // Add suggested questions - this should be visible even if the welcome message is long
    addSuggestedQuestions();
    
    // Make sure to scroll to the top of the welcome message
    setTimeout(() => {
        const firstMessage = chatBox.querySelector('.bot-message');
        if (firstMessage) {
            scrollToMessageStart(firstMessage);
        }
    }, 100);
}

// Function to hide chat popup completely
function hideChat() {
    const chatPopup = document.getElementById("chat-popup");
    const chatOpenButton = document.getElementById("chatOpenButton");
    
    if (chatPopup) {
        chatPopup.classList.add("hidden");
        // Force hide with inline style as a backup
        chatPopup.style.display = "none";
    }
    
    if (chatOpenButton) {
        chatOpenButton.textContent = "💬 Chat with us";
        chatOpenButton.classList.remove("active");
        // Make sure chat button is visible
        chatOpenButton.style.display = "block";
    }
}

// Function to show chat popup
function showChat() {
    const chatPopup = document.getElementById("chat-popup");
    const chatOpenButton = document.getElementById("chatOpenButton");
    
    if (chatPopup) {
        chatPopup.classList.remove("hidden");
        // Remove any inline display style
        chatPopup.style.display = "";
        
        // Always position the chat popup at the bottom right corner
        chatPopup.style.right = "20px";
        chatPopup.style.bottom = "20px";
        chatPopup.style.left = "auto";
        chatPopup.style.top = "auto";
    }
    
    if (chatOpenButton) {
        chatOpenButton.textContent = "Close Chat";
        chatOpenButton.classList.add("active");
    }
}

// Reset chat position - now only resets size, not position
function resetChatPosition() {
    const chatPopup = document.getElementById("chat-popup");
    
    if (chatPopup) {
        // Always maintain bottom right position
        chatPopup.style.right = "20px";
        chatPopup.style.bottom = "20px";
        chatPopup.style.left = "auto";
        chatPopup.style.top = "auto";
        
        // Reset localStorage values
        localStorage.setItem('chatbot-bottom', "20px");
        localStorage.setItem('chatbot-right', "20px");
        localStorage.removeItem('chatbot-top');
        localStorage.removeItem('chatbot-left');
        
        // Apply default width/height if needed
        chatPopup.style.width = "350px";
        chatPopup.style.height = "500px";
        localStorage.setItem('chatbot-width', "350px");
        localStorage.setItem('chatbot-height', "500px");
        
        // Ensure chat scrolls to bottom
        scrollChatToBottom();
    }
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", function() {
    // Get DOM elements - fix selector accuracy
    const chatPopup = document.getElementById("chat-popup");
    const chatOpenButton = document.getElementById("chatOpenButton");
    const chatCloseButton = document.getElementById("chatCloseButton");
    messageInput = document.getElementById("message-input");
    chatBox = document.getElementById("chat-box");
    connectionStatus = document.getElementById("connection-status");
    const sendButton = document.getElementById("send-button");
    
    // Debug - log elements to console
    console.log("Chat elements:", {
        chatPopup: chatPopup,
        chatOpenButton: chatOpenButton,
        chatCloseButton: chatCloseButton,
        messageInput: messageInput,
        chatBox: chatBox
    });
    
    // Initialize resize functionality
    initResizableChatbox();
    
    // Clear chat history on page refresh
    localStorage.removeItem('chatHistory');
    
    // Reset position if not previously set by user
    // This ensures fresh sessions always start with the chatbot at the button position
    if (!localStorage.getItem('chatbot-user-positioned')) {
        localStorage.removeItem('chatbot-top');
        localStorage.setItem('chatbot-bottom', '20px');
        localStorage.setItem('chatbot-right', '20px');
        localStorage.removeItem('chatbot-left');
    }
    
    // Ensure chat popup is always hidden on page load
    hideChat();
    
    // Generate new session ID
    sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('chatSessionId', sessionId);

    // Set up event listeners for chat open button
    if (chatOpenButton) {
        chatOpenButton.addEventListener("click", async function(e) {
            e.preventDefault();
            console.log("Chat open button clicked");
            
            if (chatPopup) {
                if (chatPopup.classList.contains("hidden")) {
                    // Open chat
                    showChat();
                    if (messageInput) messageInput.focus();
                    
                    if (connectionStatus) {
                        connectionStatus.textContent = "Connecting to Hardhat Assistant...";
                        connectionStatus.classList.remove('connected', 'disconnected');
                        connectionStatus.classList.add('connecting');
                        
                        await checkChatbotConnection();
                    }
                    
                    // Check for specific messages after opening chat
                    setTimeout(() => {
                        scrollToSixthMessage();
                    }, 300);
                } else {
                    // Close chat
                    hideChat();
                }
            }
        });
    }

    // Set up event listeners for chat close button
    if (chatCloseButton) {
        chatCloseButton.addEventListener("click", function(e) {
            e.preventDefault();
            console.log("Chat close button clicked");
            hideChat();
        });
    }

    // Initialize chat
    initializeChat();

    // Set up send button
    if (sendButton) {
        sendButton.addEventListener("click", sendMessage);
    }

    // Set up enter key for message input
    if (messageInput) {
        messageInput.addEventListener("keypress", function(e) {
            if (e.key === "Enter") {
                sendMessage();
            }
        });
    }
    
    // Setup a scroll check that monitors any changes to the chat box
    if (chatBox) {
        // Create a mutation observer to watch for changes in the chat box
        const chatObserver = new MutationObserver(function(mutations) {
            // When changes are detected, check if we need to scroll to specific messages
            scrollToSixthMessage();
        });
        
        // Start observing the chat box for changes
        chatObserver.observe(chatBox, { 
            childList: true,      // Watch for changes to the direct children
            subtree: true,        // Watch for changes to all descendants
            characterData: true   // Watch for changes to text content
        });
    }
    
    // Add a slight delay to ensure initialization is complete before hiding
    setTimeout(hideChat, 100);
    
    // If user navigates away and comes back, ensure chat is still hidden
    window.addEventListener('pageshow', function() {
        hideChat();
    });

    // Initialize chat popup position at bottom right
    if (chatPopup) {
        // Always position at bottom right regardless of saved position
        chatPopup.style.right = "20px";
        chatPopup.style.bottom = "20px";
        chatPopup.style.left = "auto";
        chatPopup.style.top = "auto";
        
        // Restore only size from localStorage
        if (localStorage.getItem('chatbot-width')) {
            chatPopup.style.width = localStorage.getItem('chatbot-width');
        }
        
        if (localStorage.getItem('chatbot-height')) {
            chatPopup.style.height = localStorage.getItem('chatbot-height');
        }
    }
}); 