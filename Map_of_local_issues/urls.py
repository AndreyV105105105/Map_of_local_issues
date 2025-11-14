# Map_of_local_issues/urls.py
from django.contrib import admin
from django.urls import path, include
from home_page.views import home_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls', namespace='users')),
    path('issues/', include('issues.urls', namespace='issues')),
    path('', home_view, name='home'),
]

# Добавляем обработку media файлов для разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)