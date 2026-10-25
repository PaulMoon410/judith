
// Chat functionality
document.addEventListener('DOMContentLoaded', function() {
    // Create chat toggle button
    const chatToggle = document.createElement('button');
    chatToggle.className = 'chat-toggle-button';
    chatToggle.innerHTML = '<i class="fas fa-comment"></i>';
    chatToggle.title = 'Chat with Harold';
    document.body.appendChild(chatToggle);

    // Create chat container
    const chatContainer = document.createElement('div');
    chatContainer.className = 'chat-container minimized';
    chatContainer.innerHTML = `
        <div class="chat-header">
            <h3><i class="fas fa-user-tie"></i> Harold</h3>
            <div class="chat-status">
                <span class="status-indicator"></span>
                <span>Online</span>
            </div>
        </div>
        <div class="chat-body">
            <div class="chat-message harold">
                Hi! I'm Harold, your electrical estimation assistant. How can I help you today?
            </div>
        </div>
        <div class="chat-input-container">
            <input type="text" class="chat-input" placeholder="Type your message..." id="chatInput">
            <button class="chat-send-button" id="chatSendButton">
                <i class="fas fa-paper-plane"></i>
            </button>
        </div>
    `;
    document.body.appendChild(chatContainer);

    // Get elements
    const chatInput = document.getElementById('chatInput');
    const chatSendButton = document.getElementById('chatSendButton');
    const chatBody = chatContainer.querySelector('.chat-body');
    const chatHeader = chatContainer.querySelector('.chat-header');

    // Toggle chat window
    chatToggle.addEventListener('click', function() {
        chatContainer.classList.toggle('minimized');
        chatToggle.classList.toggle('hidden');

        if (!chatContainer.classList.contains('minimized')) {
            chatInput.focus();
        }
    });

    // Minimize/maximize chat on header click
    chatHeader.addEventListener('click', function() {
        chatContainer.classList.add('minimized');
        chatToggle.classList.remove('hidden');
    });

    // Send message function
    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Add user message
        addMessage(message, 'user');
        chatInput.value = '';

        // Show typing indicator
        showTypingIndicator();

        // Simulate response delay
        setTimeout(() => {
            removeTypingIndicator();
            const response = getHaroldResponse(message);
            addMessage(response, 'harold');
        }, 1000 + Math.random() * 1000);
    }

    // Add message to chat
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}`;
        messageDiv.textContent = text;
        chatBody.appendChild(messageDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    // Show typing indicator
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message typing';
        typingDiv.id = 'typingIndicator';
        typingDiv.textContent = 'Harold is typing...';
        chatBody.appendChild(typingDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    // Remove typing indicator
    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // Get response from Harold (in a real app, this would be an API call)
    function getHaroldResponse(message) {
        const lowerMessage = message.toLowerCase();

        if (lowerMessage.includes('hello') || lowerMessage.includes('hi')) {
            return "Hello! I'm here to help you with electrical estimation. What would you like to know?";
        }

        if (lowerMessage.includes('price') || lowerMessage.includes('cost')) {
            return "For pricing information, please check our Materials & Pricing section. You can also upload blueprints for a detailed estimate.";
        }

        if (lowerMessage.includes('labor') || lowerMessage.includes('rate')) {
            return "Labor rates vary by location and project complexity. Use our Labor Rates tool to compare rates for different states.";
        }

        if (lowerMessage.includes('blueprint') || lowerMessage.includes('plan')) {
            return "You can upload blueprints in the Upload Blueprints section. We support PDF, DWG, and DXF formats.";
        }

        if (lowerMessage.includes('material') || lowerMessage.includes('suppl')) {
            return "Browse our materials database in the Materials & Pricing section. You can search for specific items or browse by category.";
        }

        if (lowerMessage.includes('estimate') || lowerMessage.includes('quote')) {
            return "You can create manual estimates in the Manual Estimate section. Just provide a title and description, and we'll save it for you.";
        }

        if (lowerMessage.includes('code') || lowerMessage.includes('nec')) {
            return "We use the National Electrical Code (NEC) for all calculations. You can select the appropriate code edition in Project Setup.";
        }

        if (lowerMessage.includes('residential')) {
            return "For residential projects, we focus on standard electrical requirements for homes. NEC calculations are based on square footage and circuit requirements.";
        }

        if (lowerMessage.includes('commercial') || lowerMessage.includes('industrial')) {
            return "For commercial and industrial projects, we have specific requirements based on occupancy type. Select the appropriate category in Project Setup.";
        }

        if (lowerMessage.includes('help') || lowerMessage.includes('assist')) {
            return "I'm here to help! You can ask about materials, pricing, labor rates, NEC calculations, or any other aspect of electrical estimation.";
        }

        if (lowerMessage.includes('contact') || lowerMessage.includes('support')) {
            return "For direct support, you can email us at support@judithestimator.com or call us at (555) 123-4567 during business hours.";
        }

        // Default response
        return "Thanks for your question! I'm still learning, but I'll do my best to help. Could you please provide more details?";
    }

    // Event listeners
    chatSendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Add quick replies after initial message
    setTimeout(() => {
        const quickRepliesContainer = document.createElement('div');
        quickRepliesContainer.className = 'chat-quick-replies';
        quickRepliesContainer.innerHTML = `
            <button class="quick-reply-button" onclick="sendQuickReply('What materials do you offer?')">Materials</button>
            <button class="quick-reply-button" onclick="sendQuickReply('How much do labor rates cost?')">Labor Rates</button>
            <button class="quick-reply-button" onclick="sendQuickReply('Can you help with NEC calculations?')">NEC Calculations</button>
            <button class="quick-reply-button" onclick="sendQuickReply('How do I create an estimate?')">Create Estimate</button>
        `;
        chatBody.appendChild(quickRepliesContainer);
        chatBody.scrollTop = chatBody.scrollHeight;
    }, 2000);
});

// Function to send quick reply (will be available globally)
function sendQuickReply(message) {
    // Find chat input and send the message
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = message;
        // Trigger send button click
        const sendButton = document.getElementById('chatSendButton');
        if (sendButton) {
            sendButton.click();
        }
    }
}
