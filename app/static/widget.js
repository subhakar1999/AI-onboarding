(function() {
    // Prevent multiple initializations
    if (window.AgentForgeWidgetInitialized) return;
    window.AgentForgeWidgetInitialized = true;

    // Find the script tag that loaded this script to extract configuration
    const scripts = document.getElementsByTagName('script');
    let currentScript = null;
    for (let i = 0; i < scripts.length; i++) {
        if (scripts[i].src.includes('widget.js')) {
            currentScript = scripts[i];
            break;
        }
    }

    if (!currentScript) {
        console.error("AgentForge: Could not find the widget.js script tag.");
        return;
    }

    const widgetKey = currentScript.getAttribute('data-widget-key');
    if (!widgetKey || !widgetKey.startsWith('af_pub_')) {
        console.error("AgentForge: Valid data-widget-key (starting with af_pub_) is required.");
        return;
    }

    // Base URL for the AgentForge API
    // We infer the base URL from the script src
    const widgetUrl = new URL(currentScript.src);
    const apiBaseUrl = `${widgetUrl.protocol}//${widgetUrl.host}/api/v1`;

    // Create the container element for the Shadow DOM
    const container = document.createElement('div');
    container.id = 'agentforge-widget-container';
    // Stick the container to the bottom right of the page
    container.style.position = 'fixed';
    container.style.bottom = '20px';
    container.style.right = '20px';
    container.style.zIndex = '999999';
    document.body.appendChild(container);

    // Create Shadow DOM
    const shadow = container.attachShadow({ mode: 'open' });

    // Styles for the widget (isolated from host page)
    const style = document.createElement('style');
    style.textContent = `
        :host {
            all: initial; /* Reset all inherited styles */
        }
        .widget-button {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background-color: #2563eb;
            color: white;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s;
        }
        .widget-button:hover {
            transform: scale(1.05);
        }
        .widget-button svg {
            width: 24px;
            height: 24px;
            fill: currentColor;
        }
        .chat-panel {
            display: none;
            position: absolute;
            bottom: 80px;
            right: 0;
            width: 350px;
            height: 500px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            border: 1px solid #e5e7eb;
            flex-direction: column;
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .chat-panel.open {
            display: flex;
        }
        .chat-header {
            background-color: #2563eb;
            color: white;
            padding: 16px;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .close-button {
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            font-size: 20px;
        }
        .chat-messages {
            flex-grow: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
            background-color: #f9fafb;
        }
        .message {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 18px;
            font-size: 14px;
            line-height: 1.4;
        }
        .message.user {
            background-color: #2563eb;
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        .message.agent {
            background-color: #e5e7eb;
            color: #1f2937;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
        }
        .chat-input-area {
            padding: 12px;
            border-top: 1px solid #e5e7eb;
            display: flex;
            gap: 8px;
            background: white;
        }
        .chat-input {
            flex-grow: 1;
            padding: 8px 12px;
            border: 1px solid #d1d5db;
            border-radius: 20px;
            outline: none;
            font-size: 14px;
        }
        .chat-input:focus {
            border-color: #2563eb;
        }
        .send-button {
            background-color: #2563eb;
            color: white;
            border: none;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .send-button:disabled {
            background-color: #9ca3af;
            cursor: not-allowed;
        }
    `;
    shadow.appendChild(style);

    // Chat Panel
    const chatPanel = document.createElement('div');
    chatPanel.className = 'chat-panel';
    chatPanel.innerHTML = `
        <div class="chat-header">
            <span>AgentForge Assistant</span>
            <button class="close-button">&times;</button>
        </div>
        <div class="chat-messages" id="messages">
            <div class="message agent">Hello! How can I help you today?</div>
        </div>
        <div class="chat-input-area">
            <input type="text" class="chat-input" id="message-input" placeholder="Type your message..." />
            <button class="send-button" id="send-btn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
        </div>
    `;
    shadow.appendChild(chatPanel);

    // Widget Toggle Button
    const toggleButton = document.createElement('button');
    toggleButton.className = 'widget-button';
    toggleButton.innerHTML = `
        <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
    `;
    shadow.appendChild(toggleButton);

    // Event Listeners
    let isOpen = false;
    const toggleChat = () => {
        isOpen = !isOpen;
        chatPanel.classList.toggle('open', isOpen);
    };

    toggleButton.addEventListener('click', toggleChat);
    chatPanel.querySelector('.close-button').addEventListener('click', toggleChat);

    const inputField = chatPanel.querySelector('#message-input');
    const sendBtn = chatPanel.querySelector('#send-btn');
    const messagesContainer = chatPanel.querySelector('#messages');

    const appendMessage = (text, sender) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = \`message \${sender}\`;
        msgDiv.textContent = text;
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };

    const sendMessage = async () => {
        const text = inputField.value.trim();
        if (!text) return;

        appendMessage(text, 'user');
        inputField.value = '';
        inputField.disabled = true;
        sendBtn.disabled = true;

        try {
            // Validate via the new widget execute endpoint
            const response = await fetch(\`\${apiBaseUrl}/managed/widget/execute\`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    widget_key: widgetKey,
                    message: text
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to communicate with agent.');
            }

            const data = await response.json();
            appendMessage(data.reply || 'No response received.', 'agent');

        } catch (error) {
            console.error("AgentForge Widget Error:", error);
            appendMessage(\`Error: \${error.message}\`, 'agent');
        } finally {
            inputField.disabled = false;
            sendBtn.disabled = false;
            inputField.focus();
        }
    };

    sendBtn.addEventListener('click', sendMessage);
    inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

})();
