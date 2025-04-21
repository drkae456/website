from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat_view, name='chat'),
    path('api/verify/', views.verify_connection, name='verify_connection'),  # New endpoint
    # API endpoints
    path('api/sessions/', views.session_create_api, name='create_session'),
    path('api/sessions/<str:session_id>/', views.session_detail_api, name='session_detail'),
    path('api/sessions/<str:session_id>/messages/', views.message_api, name='send_message'),
    path('api/sessions/<str:session_id>/history/', views.history_api, name='chat_history'),
] 
# API endpoints are now secured with signature-based authentication, rate limiting, and input validation