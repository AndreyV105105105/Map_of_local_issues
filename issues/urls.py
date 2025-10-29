# issues/urls.py
from django.urls import path
from . import views

app_name = 'issues'

urlpatterns = [
    path('map/', views.map_view, name='map'),
    path('create/', views.create_issue, name='create_issue'),
    path('update-status/<int:issue_id>/', views.update_issue_status, name='update_issue_status'),
]