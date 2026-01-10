/* Speech Recognition */
(function() {
    const micBtn = document.getElementById("mic-btn");
    const msgInput = document.getElementById("message-input");
    const transcriptField = document.getElementById("transcript");
    if (!micBtn) return;
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { 
        micBtn.disabled = true; 
        return; 
    }
    
    const recognizer = new SpeechRecognition();
    recognizer.lang = "en-US";
    recognizer.continuous = false;
    recognizer.interimResults = false;
    let listening = false;
    
    micBtn.addEventListener("click", () => {
        if (!listening) { 
            transcriptField.value = ""; 
            recognizer.start(); 
            listening = true; 
            micBtn.textContent = "⏹️"; 
        } else { 
            recognizer.stop(); 
        }
    });
    
    recognizer.addEventListener("result", (event) => {
        const text = Array.from(event.results).map(r => r[0].transcript).join(" ").trim();
        transcriptField.value = text; 
        msgInput.value = text;
        updateSendButton();
    });
    
    recognizer.addEventListener("end", () => { 
        listening = false; 
        micBtn.textContent = "🎙️"; 
    });
})();

/* CURRENT THREAD */
async function sendMessageAjax(message) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const threadId = window.location.pathname.split('/chat/')[1].split('/')[0];
    
    const formData = new FormData();
    formData.append('message', message);
    
    try {
        const response = await fetch(`/chat/${threadId}/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('AJAX Error:', error);
        return { response: '❌ Network error - refresh page', status: 'error' };
    }
}

function updateSendButton() {
    const msgInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    if (!msgInput || !sendBtn) return;
    
    const hasText = msgInput.value.trim().length > 0;
    sendBtn.disabled = !hasText;
    sendBtn.style.opacity = hasText ? '1' : '0.5';
}

function scrollToBottom() {
    const box = document.getElementById('messages');
    if (box) {
        box.scrollTop = box.scrollHeight;
        box.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
}

function addMessage(text, isUser) {
    const messagesBox = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `message ${isUser ? 'user' : 'bot'}`;
    div.innerHTML = `<div class="bubble">${text.replace(/\n/g, '<br>')}</div>`;
    messagesBox.appendChild(div);
    scrollToBottom();
}

/* MAIN EVENT HANDLERS */
document.addEventListener('DOMContentLoaded', function() {
    const msgInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesBox = document.getElementById('messages');
    const form = document.getElementById('chat-form');
    const docUpload = document.getElementById('doc-upload');
    
    if (!msgInput || !sendBtn || !messagesBox) return;

    // Initial scroll to bottom
    scrollToBottom();

    // Typing
    msgInput.addEventListener('input', updateSendButton);
    
    // Enter key
    msgInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey && !sendBtn.disabled) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Send button - PREVENT FORM SUBMIT (AJAX instead)
    sendBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        sendMessage();
    });
    
    // File upload - LET FORM SUBMIT (no JS prevent)
    docUpload.addEventListener('change', function() {
        if (!msgInput.value.trim()) {
            form.submit(); // File only
        }
    });
    
    // Form submit - File upload only
    form.addEventListener('submit', function(e) {
        const message = msgInput.value.trim();
        if (message) {
            e.preventDefault(); // AJAX for text
            sendMessage();
        }
        // File upload goes through normally
    });

    async function sendMessage() {
        const message = msgInput.value.trim();
        if (!message) return;
        
        // Show user message instantly (AJAX)
        addMessage(message, true);
        msgInput.value = '';
        sendBtn.disabled = true;
        sendBtn.textContent = '⏳';
        updateSendButton();
        
        // Get AI response
        const data = await sendMessageAjax(message);
        
        // Show AI response
        addMessage(data.response, false);
        
        // Reset button
        sendBtn.disabled = false;
        sendBtn.textContent = '➤';
        updateSendButton();
    }
    
    // Initial state
    updateSendButton();
});
