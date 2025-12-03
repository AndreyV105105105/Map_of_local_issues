from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomSetPasswordForm
from django.utils.translation import gettext_lazy as _

app_name = 'users'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<int:user_id>/', views.user_profile_view, name='user_profile'),
    path('my-issues/', views.user_issues_view, name='my_issues'),
    path('verify-email/<uidb64>/<token>/', views.verify_email_view, name='verify_email'),
    path('demo/start/', views.start_demo_view, name='start_demo'),
    path('demo/switch-role/', views.switch_demo_role_view, name='switch_demo_role'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='users/password_reset_form.html',
        email_template_name='emails/password_reset_email.txt',
        subject_template_name='emails/password_reset_subject.txt',
        success_url='/users/password-reset/done/',
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'
    ), name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html',
        success_url='/users/password-reset-complete/',
        form_class = CustomSetPasswordForm,
        extra_context = {'title': _('Установите новый пароль')},
    ), name='password_reset_confirm'),

    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'
    ), name='password_reset_complete'),
]