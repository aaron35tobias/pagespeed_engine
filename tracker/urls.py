# tracker/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Main dashboard view (handles both GET for UI and POST for running audits)
    path('', views.run_audit_view, name='run_audit'),
    # Internal JSON API endpoint for frontend data visualizations (Chart.js)
    path('api/history/<int:website_id>/', views.api_website_history, name='api_history'),
    path('api/websites/', views.api_recent_websites, name='api_recent_websites'),
    # Search bar autocomplete - returns reports filtered by URL query
    path('api/reports/search/', views.api_reports_search, name='api_reports_search'),
    # Delete a website + all its audit history (from the History Log delete button)
    path('websites/<int:website_id>/delete/', views.delete_website, name='delete_website'),
    
    # ── History Explorer API & Page (For your friend to work on) ──
    path('history/', views.history_page, name='history_page'),
    path('api/history/search/', views.api_history_search, name='api_history_search'),
    path('api/history/<int:report_id>/delete/', views.api_history_delete, name='api_history_delete'),
]