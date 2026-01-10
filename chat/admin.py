from django.contrib import admin
from .models import Thread, Message, Document


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'created_at']
    list_filter = ['user', 'created_at']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'thread', 'from_user', 'text', 'created_at']
    list_filter = ['thread', 'from_user', 'created_at']

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'uploaded_at']
    list_filter = ['user', 'uploaded_at']
