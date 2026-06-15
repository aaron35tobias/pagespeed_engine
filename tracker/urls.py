# tracker/urls.py

from django.urls import path
from . import views 

urlpatterns = [
    path('', views.run_audit_view, name='run_audit'),
]