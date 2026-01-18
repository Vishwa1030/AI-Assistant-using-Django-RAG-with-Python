/* SPEECH RECOGNITION */
(function() {
    const micBtn = document.getElementById("mic-btn");
    const msgInput = document.getElementById("message-input");
    const transcriptField = document.getElementById("transcript");

    if (!micBtn) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognizer = new SpeechRecognition();
    recognizer.lang = "en-US";
    recognizer.continuous = false;
    recognizer.interimResults = false;
    let listening = false;

    function startRecording() {
        micBtn.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="8" fill="currentColor"/></svg>';
        micBtn.closest('.mic-container')?.classList.add("recording");
    }

    function stopRecording() {
        micBtn.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z" stroke="currentColor" stroke-width="2"/><path d="M19 11a7 7 0 0 1-14 0" stroke="currentColor" stroke-width="2"/><path d="M12 21v-3" stroke="currentColor" stroke-width="2"/></svg>';
        micBtn.closest('.mic-container')?.classList.remove("recording");
    }

    micBtn.addEventListener("click", () => {
        if (!listening) {
            recognizer.start();
            listening = true;
            startRecording();
        } else {
            recognizer.stop();
        }
    });

    recognizer.addEventListener("result", (event) => {
        const text = event.results[0][0].transcript;
        msgInput.value = text;
        transcriptField.value = text;
        updateSendButton();
        stopRecording();
    });

    recognizer.addEventListener("end", () => {
        listening = false;
        stopRecording();
    });
})();

/* === CHATGPT PERFECT SYSTEM === */
const STORAGE_KEY = 'ai_chat_' + btoa(document.body.textContent.match(/👤\s*([^\s<]+)/)?.[1] || 'user');
let uploadedFiles = [];
let currentMessages = [];
let currentThreadId = null;
let isFirstMessage = true;

function saveHistory(history) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch(e) {}
}

function loadHistory() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch {
        return [];
    }
}

function addThread(title, messages) {
    const history = loadHistory();
    const thread = {
        id: 'chat_' + Date.now(),
        title: title.substring(0, 30) + (title.length > 30 ? '...' : ''),
        messages: messages.map(m => ({...m})),
        files: uploadedFiles.map(f => f.name), // Store file names only
        created: Date.now()
    };
    history.unshift(thread);
    if (history.length > 50) history.length = 50;
    saveHistory(history);
    return thread;
}

function updateThread(threadId, messages) {
    const history = loadHistory();
    const threadIndex = history.findIndex(t => t.id === threadId);
    if (threadIndex !== -1) {
        history[threadIndex].messages = messages.map(m => ({...m}));
        history[threadIndex].files = uploadedFiles.map(f => f.name);
        history[threadIndex].title = messages[0]?.text?.substring(0, 30) + (messages[0]?.text?.length > 30 ? '...' : '') || 'Chat';
        saveHistory(history);
    }
}

function deleteThread(threadId) {
    const history = loadHistory().filter(t => t.id !== threadId);
    saveHistory(history);
}

function getThread(threadId) {
    return loadHistory().find(t => t.id === threadId);
}

function showUploadAlert(fileCount) {
    // ✅ Insert at TOP - Chat stays visible
    currentMessages.unshift({ text: `✅ Successfully uploaded ${fileCount} file(s). Ask questions about your documents!`, isUser: false });
    renderMessages();
}

function updateSendButton() {
    const input = document.getElementById('message-input');
    const btn = document.getElementById('send-btn');
    if (input && btn) {
        const hasText = input.value.trim().length > 0;
        btn.disabled = !hasText;
        btn.style.opacity = hasText ? '1' : '0.5';
    }
}

function renderMessages() {
    const messages = document.getElementById('messages');
    if (!messages) return;
    
    // ✅ CHATGPT STYLE: Always render ALL messages
    messages.innerHTML = currentMessages.map(msg => 
        `<div class="message ${msg.isUser ? 'user' : 'bot'}">
            <div class="bubble">${msg.text.replace(/\n/g, '<br>')}</div>
        </div>`
    ).join('');
    
    // ✅ CRITICAL: Scroll + Force visible
    requestAnimationFrame(() => {
        messages.scrollTop = messages.scrollHeight;
        messages.style.minHeight = '100px'; // Prevent collapse
    });
}

function addMessage(text, isUser) {
    currentMessages.push({ text, isUser });
    
    // ✅ INSTANT render - ChatGPT style
    renderMessages();
    
    if (currentThreadId) {
        updateThread(currentThreadId, currentMessages);
        renderSidebar();
    }
}

function showMessages(messages) {
    currentMessages = messages ? messages.map(m => ({...m})) : [];
    uploadedFiles = [];
    renderMessages();
}

function renderSidebar() {
    const history = loadHistory();
    const threadList = document.getElementById('thread-list');
    if (!threadList) return;
    
    threadList.innerHTML = '';
    
    history.forEach(thread => {
        const li = document.createElement('li');
        li.className = `thread-item ${thread.id === currentThreadId ? 'active' : ''}`;
        li.dataset.threadId = thread.id;
        li.innerHTML = `
            <a href="#" class="thread-link" onclick="switchToThread('${thread.id}'); return false;">
                <span class="thread-title">${thread.title || 'New Chat'}</span>
            </a>
            <div class="thread-actions">
                <button class="delete-btn-danger" onclick="deleteChat('${thread.id}'); return false;" title="Delete">⛔</button>
            </div>
        `;
        threadList.appendChild(li);
    });
}

function resetChat() {
    currentThreadId = null;
    currentMessages = [];
    uploadedFiles = [];
    isFirstMessage = true;
    renderMessages();
    const input = document.getElementById('message-input');
    if (input) input.value = '';
    updateSendButton();
    renderSidebar();
}

function switchToThread(threadId) {
    currentThreadId = threadId;
    const thread = getThread(threadId);
    if (thread) {
        isFirstMessage = false;
        uploadedFiles = [];
        showMessages(thread.messages);
        renderSidebar();
    }
}

function deleteChat(threadId) {
    if (confirm('Delete this conversation?')) {
        deleteThread(threadId);
        if (threadId === currentThreadId) {
            resetChat();
        } else {
            renderSidebar();
        }
    }
}

async function sendMessageToServer(message) {
    const formData = new FormData();
    formData.append('message', message);
    
    // ✅ Send files if any
    uploadedFiles.forEach(file => {
        formData.append('doc_file', file);
    });
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) formData.append('csrfmiddlewaretoken', csrfToken.value);

    const response = await fetch(window.location.pathname, {
        method: 'POST',
        body: formData,
        headers: { 
            'X-Requested-With': 'XMLHttpRequest'
        }
    });
    
    if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
    }
    return await response.json();
}

function initChat() {
    renderSidebar();
    
    const urlMatch = window.location.pathname.match(/\/chat\/([a-zA-Z0-9_-]+)/);
    if (urlMatch) {
        const urlThreadId = urlMatch[1];
        const thread = getThread(urlThreadId);
        if (thread) {
            switchToThread(urlThreadId);
            return;
        }
    }
    
    resetChat();
}

document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('message-input');
    const form = document.getElementById('chat-form');
    const newChatForm = document.getElementById('new-chat-form');
    const uploadLabel = document.querySelector('.upload-icon-overlay');
    const fileInput = document.getElementById('doc-upload');

    // ✅ Initialize immediately
    initChat();
    updateSendButton();

    // ✅ File upload - Perfect handling
    if (uploadLabel && fileInput) {
        uploadLabel.addEventListener('click', () => fileInput.click());
        
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            if (files.length > 0) {
                uploadedFiles = files;
                showUploadAlert(files.length);
                e.target.value = '';
            }
        });
    }

    // ✅ New chat
    if (newChatForm) {
        newChatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            resetChat();
        });
    }

    // ✅ Send message - CHATGPT INSTANT
    if (form && input) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = input.value.trim();
            if (!message) return;

            // ✅ User message INSTANT
            addMessage(message, true);

            if (isFirstMessage) {
                const thread = addThread(message, [{ text: message, isUser: true }]);
                currentThreadId = thread.id;
                isFirstMessage = false;
            }

            input.value = '';
            updateSendButton();

            try {
                // ✅ AI reply INSTANT
                const response = await sendMessageToServer(message);
                addMessage(response.response, false);
            } catch (error) {
                console.error('Error:', error);
                addMessage('Sorry, something went wrong. Please try again.', false);
            }
        });

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                form.dispatchEvent(new Event('submit'));
            }
        });

        input.addEventListener('input', updateSendButton);
    }

    // ✅ Force chat panel visible on load
    setTimeout(() => {
        const messages = document.getElementById('messages');
        if (messages) {
            messages.style.minHeight = '200px';
            messages.style.display = 'flex';
        }
    }, 100);
});

// Global functions
window.switchToThread = switchToThread;
window.deleteChat = deleteChat;




