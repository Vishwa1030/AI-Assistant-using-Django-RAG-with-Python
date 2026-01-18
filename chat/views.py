from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib import messages  
from django.http import JsonResponse
from django.conf import settings
from .models import Thread, Message, Document
import openai
import re


openai.api_key = getattr(settings, 'OPENAI_API_KEY', None)


def get_openai_client():
    return openai

#Clean text extraction
def extract_text_from_file(file):
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
    """🎯 SINGLE  API - Handles BOTH modes perfectly"""
    try:
        client = get_openai_client()
        messages = [
            {"role": "system", "content": "You are ChatGPT, a helpful AI assistant. Answer naturally and conversationally. If document context is provided, use it to give accurate answers from user's files."}
        ]
       
        if use_documents and documents:
            messages.append({
                "role": "system",
                "content": f"CONTEXT FROM USER DOCUMENTS:\n{documents[:4000]}\n\nUse this document information when relevant."
            })
       
        if conversation_history:
            messages.append({"role": "user", "content": conversation_history})
       
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


#Get all user documents as context
def get_user_documents(user):
    docs = Document.objects.filter(user=user)
    if docs.exists():
        all_content = []
        for doc in docs[:3]:
            all_content.append(f"File: {doc.title}\n{doc.content[:3000]}")
        return "\n\n".join(all_content)
    return ""


@login_required
def chat_view(request, thread_id):
    try:
        thread = Thread.objects.get(id=thread_id, user=request.user)
    except Thread.DoesNotExist:
        thread = Thread.objects.create(user=request.user, title="New Chat")
        return redirect("chat:chat", thread_id=thread.id)
   
    threads = Thread.objects.filter(user=request.user).order_by("-created_at")
   
    if request.method == 'POST':
        if request.POST.get('action') == 'new_chat':
            new_thread = Thread.objects.create(user=request.user, title="New Chat")
            return redirect("chat:chat", thread_id=new_thread.id)
       
        message = request.POST.get('message', '').strip()
        if message:
            # AUTO-GENERATE HISTORY-BASED TITLE
            first_user_message = thread.messages.filter(from_user=True).first()
            if thread.title == "New Chat" and first_user_message is None:
                clean_message = re.sub(r'[^\w\s\?\!\.]', '', message)[:50].strip()
                sentences = re.split(r'[.!?]+', clean_message)
                title = next((s.strip().capitalize() for s in sentences if len(s.strip()) > 5), "New Chat")
                thread.title = title
                thread.save()
           
            Message.objects.create(thread=thread, from_user=True, text=message)
           
            history = ""
            recent_messages = thread.messages.order_by('-created_at')[:6]
            for msg in recent_messages:
                role = "Human" if msg.from_user else "Assistant"
                history += f"{role}: {msg.text}\n"
           
            documents = get_user_documents(request.user)
            use_documents = bool(documents)
           
            print(f"🧑 User Mode: {'📄 Documents' if use_documents else '🌐 General'} | History: {len(history)} chars")
           
            response = chat_openai(message, history, use_documents, documents)
            Message.objects.create(thread=thread, from_user=False, text=response)
           
            return JsonResponse({
                'status': 'success',
                'message': message,
                'response': response,
                'has_documents': use_documents
            })
       
        if request.FILES.get('doc_file'):
            for file in request.FILES.getlist('doc_file'):
                content = extract_text_from_file(file)
                if len(content) > 50:
                    Document.objects.create(user=request.user, title=file.name, content=content)
                    Message.objects.create(
                        thread=thread, from_user=False,
                        text=f"✅ *{file.name}* uploaded!\n\n*Preview:* {content[:250]}...\n\n🎯 Now your documents are ready! Ask me anything about them."
                    )
                else:
                    Message.objects.create(
                        thread=thread, from_user=False,
                        text=f"⚠️ *{file.name}* - No readable text found"
                    )
            return redirect("chat:chat", thread_id=thread.id)
   
    return render(request, "chat.html", {
        "threads": threads,
        "thread": thread,
        "messages": thread.messages.order_by("created_at"),
        "thread_id": thread.id
    })


@login_required
def home_redirect_view(request):
    thread = Thread.objects.filter(user=request.user).order_by("-created_at").first()
    if not thread:
        thread = Thread.objects.create(user=request.user, title="New Chat")
    return redirect("chat:chat", thread_id=thread.id)


@login_required
def delete_thread(request, thread_id):
    if request.method == "POST":
        Thread.objects.filter(id=thread_id, user=request.user).delete()
    new_thread = Thread.objects.create(user=request.user, title="New Chat")
    return redirect("chat:chat", thread_id=new_thread.id)


@login_required
def delete_message(request, message_id):
    if request.method == "POST":
        try:
            msg = Message.objects.get(id=message_id, thread__user=request.user)
            thread_id = msg.thread.id
            msg.delete()
            return redirect("chat:chat", thread_id=thread_id)
        except:
            pass
    return redirect("chat:chat", thread_id=1)


@login_required
def clear_history(request):
    if request.method == "POST":
        Thread.objects.filter(user=request.user).delete()
        Document.objects.filter(user=request.user).delete()
    new_thread = Thread.objects.create(user=request.user, title="New Chat")
    return redirect("chat:chat", thread_id=new_thread.id)


# FIXED SIGNUP 
def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                thread = Thread.objects.create(user=user, title=f"{user.username}'s Chat")
                messages.success(request, f"Welcome {user.username}! Chat ready!")
                return redirect("chat:chat", thread_id=thread.id)
            except Exception as e:
                messages.error(request, "Error creating account. Try different username.")
                form.add_error(None, "Username may already exist.")
        else:
            messages.error(request, "Please fix form errors below.")
    else:
        form = UserCreationForm()
    return render(request, "signup.html", {"form": form})


# FIXED LOGIN - Shows proper errors
def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            thread = Thread.objects.filter(user=user).order_by("-created_at").first()
            if not thread:
                thread = Thread.objects.create(user=user, title=f"{user.username}'s Chat")
            messages.success(request, f"Welcome back {user.username}!")
            return redirect("chat:chat", thread_id=thread.id)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect("chat:login") 