from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView
from users.forms import CustomAuthenticationForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(
        form_class=CustomAuthenticationForm,
        template_name='registration/login.html'
    ), name='login'),
    path('', include('home_page.urls')),
    # Add other app URLs here
]