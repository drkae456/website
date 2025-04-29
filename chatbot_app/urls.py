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
    path('test-logging/', views.test_logging, name='test_logging'),
    path('test-fuzzy/', views.test_fuzzy_search, name='test_fuzzy_search'),
    path('analyze-fuzzy/', views.analyze_fuzzy_search, name='analyze_fuzzy_search'),
    path('test-search/', views.test_search_page, name='test_search_page'),
] 
# API endpoints are now secured with signature-based authentication, rate limiting, and input validation