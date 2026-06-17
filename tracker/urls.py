# tracker/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.run_audit_view, name='run_audit'),
    path('api/history/<int:website_id>/', views.api_website_history, name='api_history'),
    path('api/websites/', views.api_recent_websites, name='api_recent_websites'),
]