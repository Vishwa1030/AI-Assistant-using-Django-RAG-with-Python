from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home_redirect_view, name='home'),
    path('chat/<int:thread_id>/', views.chat_view, name='chat'),
    path('delete/<int:thread_id>/', views.delete_thread, name='delete_thread'),
    path('clear/', views.clear_history, name='clear_history'),
    path('delete-message/<int:message_id>/', views.delete_message, name='delete_message'),
]


    












