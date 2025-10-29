# Map_of_local_issues/urls.py
from django.contrib import admin
from django.urls import path, include
from home_page.views import home_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls', namespace='users')),
    path('issues/', include('issues.urls', namespace='issues')),
    path('', home_view, name='home'),
]