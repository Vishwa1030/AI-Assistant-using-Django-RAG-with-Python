from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.conf import settings
from django.contrib import messages
from .models import Thread, Message, Document
import openai
import re

openai.api_key = getattr(settings, 'OPENAI_API_KEY', None)

def get_openai_client():
    return openai

def extract_text_from_file(file):
    #Clean text extraction
    try:
        content = file.read().decode('utf-8', errors='ignore')
        content = re.sub(r'PDF-\d\.\d|%PDF-\d\.\d|PK\s*\d|word/document\.xml|DOCX|ZIP', '', content)
        content = re.sub(r'[^\w\s\.\,\!\?\-\(\)\:\;\'\"\n\r]', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip()
        content = re.sub(r'\b\w{1,2}\b\s?', '', content)
        content = re.sub(r'\s+', ' ', content).strip()
        return content[:10000]
    except:
        return "Document content extracted"

def chat_openai(message, conversation_history="", use_documents=False, documents=""):
    #Generate response
    try:
        client = get_openai_client()
        
        # Build conversation context
        messages = [
            {"role": "system", "content": "A helpful AI assistant. Answer naturally and conversationally. If document context is provided, use it to give accurate answers from user's files."}
        ]
        
        # Add document context if available
        if use_documents and documents:
            messages.append({
                "role": "system", 
                "content": f"CONTEXT FROM USER DOCUMENTS:\n{documents[:4000]}\n\nUse this document information when relevant."
            })
        
        # Add conversation history
        if conversation_history:
            messages.append({"role": "user", "content": conversation_history})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1200,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"OpenAI error: {e}")
        return "I'm having trouble connecting right now. Please try again!"

def get_user_documents(user):
    docs = Document.objects.filter(user=user).order_by('-id')  #
    
    if not docs.exists():
        return ""
    
    print(f"📁 Found {docs.count()} total documents")
    
    #Top relevant docs + summaries
    all_context = []
    total_chars = 0
    
    for i, doc in enumerate(docs):
        # Chunk large docs
        doc_preview = doc.content[:1500]  # Short preview for context
        doc_summary = f"📄 **{doc.title}** ({len(doc.content)} chars): {doc_preview}"
        
        all_context.append(doc_summary)
        total_chars += len(doc_summary)
        
        # Stop if too long (GPT limit)
        if total_chars > 12000:
            all_context.append(f"... and {docs.count() - i - 1} more documents")
            break
    
    full_context = "\n\n".join(all_context)
    print(f"📦 Context sent: {len(full_context)} chars from {len(all_context)} doc previews")
    return full_context

def chat_perfect_gpt(message, user_context=""):
    #Single  API - Handles unlimited documents
    try:
        client = get_openai_client()
        
        system_prompt = """You are ChatGPT, a helpful AI assistant.

DOCUMENT CONTEXT:
- Multiple user documents available (resumes, projects, etc.)
- Each document shows filename + preview/summary
- Use document information when user asks about their files
- Say "From your [filename]:" when referencing specific docs

General behavior:
- Answer naturally and conversationally
- Reference specific documents when relevant"""

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if user_context:
            messages.append({
                "role": "system",
                "content": f"USER DOCUMENTS:\n{user_context}"
            })
        
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1500,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"GPT Error: {e}")
        return "Let me help you! (Processing documents...)"

@login_required
def chat_view(request, thread_id):
    try:
        thread = Thread.objects.get(id=thread_id, user=request.user)
    except Thread.DoesNotExist:
        thread = Thread.objects.create(user=request.user, title="New Chat")
        return redirect("chat", thread_id=thread.id)
    
    threads = Thread.objects.filter(user=request.user).order_by("-created_at")
    
    if request.method == 'POST':
        if request.POST.get('action') == 'new_chat':
            new_thread = Thread.objects.create(user=request.user, title="New Chat")
            return redirect("chat", thread_id=new_thread.id)
        
        message = request.POST.get('message', '').strip()
        if message:
            # Save user message
            Message.objects.create(thread=thread, from_user=True, text=message)
            
            # Get conversation history
            history = ""
            recent_messages = thread.messages.order_by('-created_at')[:6]
            for msg in recent_messages:
                role = "Human" if msg.from_user else "Assistant"
                history += f"{role}: {msg.text}\n"
            
            # Check if user has documents
            documents = get_user_documents(request.user)
            use_documents = bool(documents)
            
            print(f"🧑 User: {'📄 Documents' if use_documents else '🌐 General'} | History: {len(history)} chars")
            
            # Single ChatGPT call - handles everything!
            response = chat_openai(message, history, use_documents, documents)
            
            # Save AI response
            Message.objects.create(thread=thread, from_user=False, text=response)
            
            return JsonResponse({
                'status': 'success',
                'message': message,
                'response': response,
                'has_documents': use_documents
            })
        
        # File upload
        if request.FILES.get('doc_file'):
            for file in request.FILES.getlist('doc_file'):
                content = extract_text_from_file(file)
                if len(content) > 50:
                    Document.objects.create(user=request.user, title=file.name, content=content)
                    Message.objects.create(
                        thread=thread, from_user=False,
                        text=f"✅ **{file.name}** uploaded!\n\n"
                            f"**Preview:** {content[:250]}...\n\n"
                            f"🎯 Now your documents are ready! Ask me anything about them."
                    )
                else:
                    Message.objects.create(
                        thread=thread, from_user=False,
                        text=f"⚠️ **{file.name}** - No readable text found"
                    )
            return redirect("chat", thread_id=thread.id)
    
    return render(request, "chat.html", {
        "threads": threads,
        "thread": thread,
        "messages": thread.messages.order_by("created_at"),
        "thread_id": thread.id
    })

# All other views 
@login_required
def home_redirect_view(request):
    thread = Thread.objects.filter(user=request.user).order_by("-created_at").first()
    if not thread:
        thread = Thread.objects.create(user=request.user, title="New Chat")
    return redirect("chat", thread_id=thread.id)

@login_required
def delete_thread(request, thread_id):
    if request.method == "POST":
        Thread.objects.filter(id=thread_id, user=request.user).delete()
    new_thread = Thread.objects.create(user=request.user, title="New Chat")
    return redirect("chat", thread_id=new_thread.id)

@login_required
def delete_message(request, message_id):
    if request.method == "POST":
        try:
            msg = Message.objects.get(id=message_id, thread__user=request.user)
            thread_id = msg.thread.id
            msg.delete()
            return redirect("chat", thread_id=thread_id)
        except:
            pass
    return redirect("home")

@login_required
def clear_history(request):
    if request.method == "POST":
        Thread.objects.filter(user=request.user).delete()
        Document.objects.filter(user=request.user).delete()
    new_thread = Thread.objects.create(user=request.user, title="New Chat")
    return redirect("chat", thread_id=new_thread.id)

def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()  # Create user
            return redirect("login")
    else:
        form = UserCreationForm()
    return render(request, "signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            from .models import Thread
            thread = Thread.objects.filter(user=user).order_by("-created_at").first()
            if not thread:
                thread = Thread.objects.create(user=user, title=f"{user.username}'s Chat")
            return redirect("chat", thread_id=thread.id)
        else:
            messages.error(request, "No account found? Create one!")
            return redirect("signup")
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form})



def logout_view(request):
    logout(request)
    messages.info(request, "Log out successfully.")
    return redirect("login")
