from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.db import connection
from home_page.views import home_view, about_site
from django.conf import settings
from django.conf.urls.static import static


def health_view(_request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({'status': 'error'}, status=503)
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls', namespace='users')),
    path('issues/', include('issues.urls', namespace='issues')),
    path('', home_view, name='home'),
    path('about/', about_site, name='about_site'),
    path('health/', health_view, name='health'),
]

# Добавляем обработку media файлов для разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)