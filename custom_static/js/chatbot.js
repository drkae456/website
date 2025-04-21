// Global variables
let currentUser = { isLoggedIn: false, name: 'Guest' };
let chatHistory = []; // Array to hold message objects { sender: 'user'/'bot', text: 'message', timestamp: number }
let messageInput;
let chatBox;
let sessionId;
let connectionStatus;

// Update the chatbot server URL to use separate port
const CHATBOT_SERVER_URL = window.location.protocol + '//' + window.location.hostname + ':8001/chatbot';

// Global helper functions
function saveChatHistory() {
  try {
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
  } catch (e) {
    console.error("Error saving chat history:", e);
    // Handle potential storage limits or errors
  }
}

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
    // Use logged-in user's name or 'Guest'
    prefix = `${currentUser.isLoggedIn ? currentUser.name : 'Guest'}: `;
    messageDiv.textContent = prefix + messageObject.text;
  } else if (isBot) {
    prefix = 'Hardie Hat 🤖: ';
    // Process URLs and line breaks in the bot's message
    let formattedMessage = messageObject.text || ""; // Ensure text is not undefined
    formattedMessage = formattedMessage.replace(/\\n/g, '<br>');
    const pathRegex = /(\/[\\w\/-]+)/g; // Simpler regex, adjust if needed
    formattedMessage = formattedMessage.replace(pathRegex, '<a href="$1" target="_blank">$1</a>');
    messageDiv.innerHTML = prefix + formattedMessage;
  } else if (isIndicator) {
     messageDiv.id = 'typing-indicator';
     messageDiv.textContent = messageObject.text; // e.g., 'Hardie Hat is typing...'
  }

  chatBox.appendChild(messageDiv);

  // Add to history array ONLY if it's a user or bot message AND we are NOT loading history
  if ((isUser || isBot) && !isLoadingHistory) {
      // Ensure timestamp exists
      messageObject.timestamp = messageObject.timestamp || Date.now();
      // Add to array and save
      chatHistory.push(messageObject);
      saveChatHistory();
  }

  // Ensure smooth scrolling to bottom
  // Use requestAnimationFrame for potentially smoother scrolling
  requestAnimationFrame(() => {
      chatBox.scrollTop = chatBox.scrollHeight;
  });
}

function addTypingIndicator() {
  removeTypingIndicator(); // Ensure only one indicator at a time
  addMessage({ sender: 'indicator', text: 'Hardie Hat is typing...' });
}

function removeTypingIndicator() {
  const indicator = document.getElementById('typing-indicator');
  if (indicator) {
    indicator.remove();
  }
}

// Function to get user information
function getUserInfo() {
  // Make an async request to get user information
  return new Promise((resolve, reject) => {
    fetch('/get-current-user/', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.is_authenticated) {
        resolve({ 
          isLoggedIn: true, 
          name: data.first_name || 'User', // Use first name if available, or "User" as fallback
          id: data.id
        });
      } else {
        resolve({ isLoggedIn: false, name: 'Guest' });
      }
    })
    .catch(error => {
      console.error('Error fetching user info:', error);
      resolve({ isLoggedIn: false, name: 'Guest' }); // Default to guest on error
    });
  });
}

// Global sendMessage function
function sendMessage(directMessage = null) {
  if (!messageInput) {
    messageInput = document.getElementById("message-input");
  }
  
  // Use either the direct message or the input value
  const messageText = directMessage || (messageInput ? messageInput.value.trim() : '');
  
  if (messageText) {
    // Refresh user info before sending the message
    getUserInfo().then(userInfo => {
      // Update current user
      currentUser = userInfo;
      
      // Create user message object
      const userMessage = {
          sender: 'user',
          text: messageText,
          timestamp: Date.now()
      };
      // Add user message to display & history
      addMessage(userMessage);
      
      // Clear input if we used it
      if (!directMessage && messageInput) {
        messageInput.value = '';
      }
      
      // Show typing indicator
      addTypingIndicator();
      
      // Get the session ID
      let curSessionId = sessionId || localStorage.getItem('chatSessionId');
      
      // If no session ID, create a new one
      if (!curSessionId) {
        createNewSession().then(newSessionId => {
          if (newSessionId) {
            curSessionId = newSessionId;
            sendMessageToServer(messageText, curSessionId);
          } else {
            handleSendError("Could not create a chat session");
          }
        });
      } else {
        sendMessageToServer(messageText, curSessionId);
      }
    });
  }
}

// Function to actually send the message to the server
function sendMessageToServer(messageText, curSessionId) {
  fetch(`${CHATBOT_SERVER_URL}/chat/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    credentials: 'include', // Include cookies
    body: JSON.stringify({
      message: messageText,
      session_id: curSessionId
    })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    removeTypingIndicator();
    
    // Create bot message object
    const botResponse = {
        sender: 'bot',
        text: data.response || "Sorry, I couldn't process that.",
        timestamp: Date.now()
    };
    // Add response using the new addMessage function
    addMessage(botResponse);
    
    // Scroll to bottom (addMessage already handles this, but keep for safety)
    if (chatBox) {
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  })
  .catch(error => {
    handleSendError(error.message);
  });
}

// Handle send errors
function handleSendError(errorMessage) {
  removeTypingIndicator();
  
  // Log the error
  console.error('Error sending message:', errorMessage);
  
  // Add error message object
  const botErrorMessage = {
      sender: 'bot', // Display as a bot message
      text: "Sorry, I'm having trouble connecting. Please try again later.",
      timestamp: Date.now()
  };
  addMessage(botErrorMessage);
  
  // Check connection again
  checkChatbotConnection();
}

// Function to check chatbot connection
async function checkChatbotConnection() {
    connectionStatus.textContent = "Connecting to Hardie Hat...";
    connectionStatus.classList.remove('connected', 'disconnected');
    connectionStatus.classList.add('connecting');
    
    try {
        const response = await fetch(`${CHATBOT_SERVER_URL}/api/verify/`, {
            credentials: 'include', // Include cookies
            headers: {
                'Accept': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            connectionStatus.textContent = "You have been connected to Hardie Hat";
            connectionStatus.classList.remove('connecting');
            connectionStatus.classList.add('connected');
            
            // Add session ID to local storage if not already there
            if (!localStorage.getItem('chatSessionId')) {
                createNewSession();
            }
            
            return true;
        } else if (data.status === 'partial') {
            // Partial connection - the server has database access but might have cross-app issues
            connectionStatus.textContent = "Connected with limited functionality. Some features may not work.";
            connectionStatus.classList.remove('connecting');
            connectionStatus.classList.add('connected');
            console.warn("Chatbot connected with partial functionality:", data.message, data.diagnostics);
            
            // Create a new session anyway
            if (!localStorage.getItem('chatSessionId')) {
                createNewSession();
            }
            
            return true;
        } else {
            connectionStatus.textContent = "Unable to connect to Hardie Hat: " + data.message;
            connectionStatus.classList.remove('connecting');
            connectionStatus.classList.add('disconnected');
            console.error("Chatbot connection error:", data);
            return false;
        }
    } catch (error) {
        connectionStatus.textContent = "Error connecting to Hardie Hat. Is the chatbot server running?";
        connectionStatus.classList.remove('connecting');
        connectionStatus.classList.add('disconnected');
        console.error("Chatbot connection error:", error);
        return false;
    }
}

// Function to create a new chat session
async function createNewSession() {
    try {
        const response = await fetch(`${CHATBOT_SERVER_URL}/api/sessions/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include' // Include cookies
        });
        
        if (response.ok) {
            const data = await response.json();
            // Save session ID to localStorage
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

document.addEventListener("DOMContentLoaded", function () {
  const chatPopup = document.getElementById("chat-popup");
  const chatOpenButton = document.getElementById("chatOpenButton");
  const chatCloseButton = document.getElementById("chatCloseButton");
  messageInput = document.getElementById("message-input");
  chatBox = document.getElementById("chat-box");
  connectionStatus = document.getElementById("connection-status");
  const sendButton = document.getElementById("send-button");
  const fullscreenButton = document.getElementById("fullscreenButton");
  
  // Clear chat history on page refresh
  localStorage.removeItem('chatHistory');
  
  // IMPORTANT - Make sure the chat popup is never in fullscreen mode on page load
  if (chatPopup && chatPopup.classList.contains("fullscreen-chat")) {
    chatPopup.classList.remove("fullscreen-chat");
  }
  
  // Generate a new session ID on every page load
  sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  localStorage.setItem('chatSessionId', sessionId);

  // Remove fullscreen class if it exists in localStorage
  if (localStorage.getItem('chatFullscreen') === 'true') {
    localStorage.removeItem('chatFullscreen');
  }

  // Toggle the chat popup (Ensure elements exist)
  if (chatOpenButton && chatPopup && messageInput) {
    chatOpenButton.addEventListener("click", async function () {
      if (chatPopup.classList.contains("hidden")) {
        // Open the chat
        chatPopup.classList.remove("hidden");
        if (chatPopup.classList.contains("fullscreen-chat")) {
          chatPopup.classList.remove("fullscreen-chat");
        }
        messageInput.focus();
        chatOpenButton.textContent = "Close Chat";
        chatOpenButton.classList.add("active");
        
        // Reset connection status
        connectionStatus.textContent = "Connecting to Hardie Hat...";
        connectionStatus.classList.remove('connected', 'disconnected');
        connectionStatus.classList.add('connecting');
        
        // Check connection
        await checkChatbotConnection();
      } else {
        // Close the chat
        chatPopup.classList.add("hidden");
        chatOpenButton.textContent = "Chat with Us";
        chatOpenButton.classList.remove("active");
      }
    });
  } else {
    console.error("Chat open button, popup, or message input not found.");
  }

  // Close the chat popup (Ensure elements exist)
  if (chatCloseButton && chatPopup && chatOpenButton) {
    chatCloseButton.addEventListener("click", function () {
      chatPopup.classList.add("hidden");
      if (chatOpenButton) {
        chatOpenButton.textContent = "Chat with Us";
        chatOpenButton.classList.remove("active");
      }
    });
  } else {
     console.error("Chat close button, popup, or open button not found.");
  }

  // Fullscreen Button Logic
  if (fullscreenButton && chatPopup && chatBox) {
    // Toggle fullscreen mode function
    function toggleFullscreen() {
      // Add transition for smoother resize
      chatPopup.style.transition = 'all 0.3s ease-in-out';
      
      chatPopup.classList.toggle("fullscreen-chat");
      if (chatPopup.classList.contains("fullscreen-chat")) {
        fullscreenButton.innerHTML = "⮌"; // Minimize icon
        fullscreenButton.title = "Exit fullscreen";
        document.body.classList.add("chat-fullscreen-active"); // Add class to body
      } else {
        fullscreenButton.innerHTML = "⛶"; // Expand icon
        fullscreenButton.title = "Enter fullscreen";
        document.body.classList.remove("chat-fullscreen-active"); // Remove class from body
      }

      // Ensure chat resizes smoothly and scrolls to bottom
      setTimeout(() => {
        chatBox.scrollTop = chatBox.scrollHeight;
        // Reset transition after animation completes
        setTimeout(() => {
          chatPopup.style.transition = '';
        }, 300);
      }, 100);
    }

    // Add event listener to the existing fullscreen button
    fullscreenButton.addEventListener("click", toggleFullscreen);
  } else {
    if (!fullscreenButton) console.error("Fullscreen button element not found in HTML.");
    if (!chatPopup) console.error("Chat popup element not found for fullscreen toggle.");
    if (!chatBox) console.error("Chat box element not found for scroll adjustment.");
  }

  // Load chat history from localStorage
  function loadChatHistory() {
    if (!chatBox) return []; // Can't load if chatBox doesn't exist yet
    const savedHistory = localStorage.getItem('chatHistory');
    if (savedHistory) {
      try {
        const parsedHistory = JSON.parse(savedHistory);
        // Clear the chatbox before loading
        chatBox.innerHTML = '';
        // Add messages from history
        parsedHistory.forEach(msg => addMessage(msg, true)); // Pass flag to prevent re-saving during load
        return parsedHistory; // Return the loaded history
      } catch (e) {
        console.error("Error parsing chat history:", e);
        localStorage.removeItem('chatHistory'); // Clear corrupted history
        return [];
      }
    }
    return [];
  }

  // Add suggested questions
  function addSuggestedQuestions() {
    if (!chatBox) return; // Need chatBox to append suggestions
    // Check if suggestions already exist to avoid duplicates
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
    
    // Scroll to bottom after adding suggestions
    requestAnimationFrame(() => {
      chatBox.scrollTop = chatBox.scrollHeight;
    });
  }

  // Modified initializeChat to always show welcome message
  function initializeChat() {
     if (!chatBox) {
        console.error("Chat box not found during initialization.");
        return; // Can't initialize without chatBox
    }
    
    // Reset chat history array
    chatHistory = [];
    
    // Get user info first, then initialize the chat
    getUserInfo().then(userInfo => {
      // Update current user
      currentUser = userInfo;
      
      // Always add initial welcome message and suggestions since history is cleared on refresh
      const welcomeMessage = {
          sender: 'bot',
          text: "Hello! Welcome to Hardhat Enterprises. My name is Hardie Hat I am here to help you explore the world of Hardhat Enterprises.",
          timestamp: Date.now()
      };
      addMessage(welcomeMessage); // Adds to DOM and history array
      addSuggestedQuestions();

      // Ensure latest message is visible
      setTimeout(() => {
        chatBox.scrollTop = chatBox.scrollHeight;
      }, 100); // Slight delay to ensure rendering completes
    });
  }
  
  // Initialize chat when loaded
  initializeChat();

  // Attach click event listener to send button
  if (sendButton) { // Check send button exists
      sendButton.addEventListener("click", sendMessage);
  } else {
      console.error("Send button not found.");
  }

  // Allow sending message with Enter key
  if (messageInput) { // Check input exists
      messageInput.addEventListener("keypress", function(e) {
        if (e.key === "Enter") {
          sendMessage();
        }
      });
  } else {
      console.error("Message input not found for keypress listener.");
  }
}); 