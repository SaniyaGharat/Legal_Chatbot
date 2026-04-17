// static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const resetButton = document.getElementById('reset-btn');
    const categoriesList = document.getElementById('categories-list');
    const historyList = document.getElementById('history-list');
    const languageSelect = document.getElementById('language-select');
    const printBtn = document.getElementById('print-btn');
    const fileUpload = document.getElementById('file-upload');
    const uploadBtn = document.getElementById('upload-btn');
    const voiceBtn = document.getElementById('voice-btn');
    const filePreview = document.getElementById('file-preview');
    const templatesList = document.getElementById('templates-list');
    
    // State
    let conversationId = 'default-' + Date.now();
    let isWaitingForResponse = false;
    let selectedFiles = [];
    let isRecording = false;
    let recognition = null;
    let currentTemplate = '';
    
    // Load initial data
    loadLegalCategories();
    loadTemplates();
    loadHistory();
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    resetButton.addEventListener('click', resetConversation);
    printBtn.addEventListener('click', () => window.print());
    
    uploadBtn.addEventListener('click', () => fileUpload.click());
    fileUpload.addEventListener('change', handleFileSelect);
    
    voiceBtn.addEventListener('click', toggleVoiceInput);
    
    // Initialize speech recognition if supported
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            userInput.value += transcript;
            stopRecording();
        };
        
        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            stopRecording();
        };
        
        recognition.onend = () => {
            stopRecording();
        };
    } else {
        voiceBtn.style.display = 'none';
    }
    
    // Functions
    function loadLegalCategories() {
        fetch('/api/legal_categories')
            .then(response => response.json())
            .then(categories => {
                categoriesList.innerHTML = '';
                categories.forEach(category => {
                    const li = document.createElement('li');
                    li.textContent = category.name;
                    li.dataset.id = category.id;
                    li.addEventListener('click', () => {
                        userInput.value = `Tell me about ${category.name} in India`;
                        userInput.focus();
                    });
                    categoriesList.appendChild(li);
                });
            })
            .catch(error => console.error('Error loading categories:', error));
    }
    
    function loadTemplates() {
        fetch('/api/templates')
            .then(response => response.json())
            .then(templates => {
                templatesList.innerHTML = '';
                templates.forEach(template => {
                    const li = document.createElement('li');
                    li.innerHTML = `<span>${template.icon}</span> ${template.name}`;
                    li.dataset.id = template.id;
                    li.addEventListener('click', () => {
                        // Start a new conversation for the template
                        resetConversation();
                        currentTemplate = template.name;
                        userInput.value = `I want to draft a ${template.name} step-by-step. Please guide me through the process.`;
                        userInput.focus();
                        // Delay slightly to ensure reset is complete
                        setTimeout(sendMessage, 500);
                    });
                    templatesList.appendChild(li);
                });
            })
            .catch(error => console.error('Error loading templates:', error));
    }
    
    function loadHistory() {
        fetch('/api/conversations')
            .then(response => response.json())
            .then(conversations => {
                historyList.innerHTML = '';
                conversations.forEach(conv => {
                    const li = document.createElement('li');
                    li.textContent = conv.title;
                    li.dataset.id = conv.id;
                    li.title = conv.title;
                    if (conv.id === conversationId) {
                        li.classList.add('active');
                    }
                    li.addEventListener('click', () => {
                        if (conv.id !== conversationId) {
                            loadConversation(conv.id);
                        }
                    });
                    historyList.appendChild(li);
                });
            })
            .catch(error => console.error('Error loading history:', error));
    }
    
    function loadConversation(id) {
        if (isWaitingForResponse) return;
        
        conversationId = id;
        
        // Update active class in sidebar
        const items = historyList.querySelectorAll('li');
        items.forEach(item => {
            item.classList.toggle('active', item.dataset.id === id);
        });
        
        // Fetch history for this ID
        fetch(`/api/conversation/${id}`)
            .then(response => response.json())
            .then(data => {
                // Clear chat UI
                chatMessages.innerHTML = '';
                
                // Add back the initial assistant message then the history
                addWelcomeMessage();
                
                if (data.history) {
                    data.history.forEach(msg => {
                        addMessageToChat(msg.role === 'assistant' ? 'assistant' : 'user', msg.content, false);
                    });
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            })
            .catch(error => console.error('Error loading conversation:', error));
    }

    function addWelcomeMessage() {
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'message assistant';
        welcomeDiv.innerHTML = `
            <div class="message-content">
                <p>Namaste! I'm your Indian Legal Assistant. How can I help you with Indian law today?</p>
            </div>
        `;
        chatMessages.appendChild(welcomeDiv);
    }
    
    function handleFileSelect(event) {
        const files = Array.from(event.target.files);
        if (files.length > 0) {
            selectedFiles = [files[0]]; // Support single file for now
            updateFilePreview();
        }
    }
    
    function updateFilePreview() {
        if (selectedFiles.length > 0) {
            filePreview.innerHTML = `
                <span>📎 ${selectedFiles[0].name}</span>
                <button class="icon-btn-sm" id="remove-file">✕</button>
            `;
            filePreview.style.display = 'flex';
            document.getElementById('remove-file').addEventListener('click', () => {
                selectedFiles = [];
                filePreview.style.display = 'none';
                fileUpload.value = '';
            });
        } else {
            filePreview.style.display = 'none';
        }
    }
    
    function toggleVoiceInput() {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    }
    
    function startRecording() {
        if (!recognition) return;
        try {
            recognition.start();
            isRecording = true;
            voiceBtn.classList.add('active');
            voiceBtn.textContent = '⏹️';
        } catch (e) {
            console.error(e);
        }
    }
    
    function stopRecording() {
        if (!recognition) return;
        recognition.stop();
        isRecording = false;
        voiceBtn.classList.remove('active');
        voiceBtn.textContent = '🎤';
    }

    function sendMessage() {
        const message = userInput.value.trim();
        if (message === '' && selectedFiles.length === 0) return;
        if (isWaitingForResponse) return;
        
        // Add user message to chat
        const displayMessage = message || `[Uploaded Document: ${selectedFiles[0].name}]`;
        addMessageToChat('user', displayMessage);
        
        // Prepare data
        const formData = new FormData();
        formData.append('message', message);
        formData.append('conversation_id', conversationId);
        formData.append('language', languageSelect.value);
        if (selectedFiles.length > 0) {
            formData.append('files', selectedFiles[0]);
        }
        
        // Clear input and preview
        userInput.value = '';
        selectedFiles = [];
        updateFilePreview();
        
        // Show loading indicator
        isWaitingForResponse = true;
        const loadingDiv = addLoadingIndicator();
        
        // Send to backend
        fetch('/api/chat', {
            method: 'POST',
            body: formData,
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading indicator
            if (loadingDiv && loadingDiv.parentNode) {
                loadingDiv.parentNode.removeChild(loadingDiv);
            }
            
            if (data.error) {
                addMessageToChat('assistant', 'Sorry, there was an error: ' + data.error);
            } else {
                addMessageToChat('assistant', data.response);
                // Refresh history list
                loadHistory();
            }
        })
        .catch(error => {
            if (loadingDiv && loadingDiv.parentNode) {
                loadingDiv.parentNode.removeChild(loadingDiv);
            }
            addMessageToChat('assistant', 'NOTICE: My AI cores are currently experiencing heavy traffic. Please use the sidebar templates or try again in a few moments.');
            console.error('Error:', error);
        })
        .finally(() => {
            isWaitingForResponse = false;
        });
    }
    
    function addMessageToChat(role, content, shouldScroll = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Use marked.js for Markdown rendering
        marked.setOptions({
            breaks: true,
            gfm: true
        });
        
        // Render markdown
        let htmlContent = marked.parse(content);
        
        // Post-process for legal citations (so they still get the custom class)
        htmlContent = htmlContent.replace(/Section (\d+[A-Za-z]?) of ([\w\s]+) Act/g, (match, sec, act) => {
            const query = encodeURIComponent(`Section ${sec} of ${act} IndiaCode`);
            return `<a href="https://www.google.com/search?q=${query}" target="_blank" class="citation">Section ${sec} of ${act} Act</a>`;
        });
        
        contentDiv.innerHTML = htmlContent;
        messageDiv.appendChild(contentDiv);

        // Removed PDF button logic as per user request to remove feature.
        
        chatMessages.appendChild(messageDiv);
        
        if (shouldScroll) {
            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
    
    function addLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message assistant';
        loadingDiv.innerHTML = `
            <div class="message-content loading">
                <p>Thinking...</p>
            </div>
        `;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return loadingDiv;
    }
    
    function resetConversation() {
        // Generate new conversation ID
        conversationId = 'default-' + Date.now();
        
        // Clear chat UI and show welcome message
        chatMessages.innerHTML = '';
        addWelcomeMessage();
        
        // Update history UI (clear active state)
        loadHistory();
        
        // Reset on server
        fetch('/api/reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                conversation_id: conversationId
            }),
        }).catch(error => console.error('Error resetting conversation:', error));
    }
});