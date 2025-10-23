from django.contrib import admin
from django.urls import path, include
from home_page.views import home_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls', namespace='users')),
    path('', home_view, name='home'),
]