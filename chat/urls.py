from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # HOME = LOGIN FIRST (No chat without login)
    path('', views.login_view, name='home'),
    
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Chat (Protected)
    path('chat/', views.home_redirect_view, name='chat_home'),
    path('chat/<int:thread_id>/', views.chat_view, name='chat'),
    path('delete-thread/<int:thread_id>/', views.delete_thread, name='delete_thread'),
    path('clear-history/', views.clear_history, name='clear_history'),
]

    












