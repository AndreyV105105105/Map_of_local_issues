from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.utils.translation import gettext_lazy as _
import re
User = get_user_model()


@login_required
def profile_view(request):
    return render(request, 'users/profile.html')


def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        # 1. Проверяем, есть ли уже пользователь с таким email
        try:
            existing_user = User.objects.get(email=email)
        except User.DoesNotExist:
            existing_user = None

        form = CustomUserCreationForm(request.POST)

        if existing_user:
            if not existing_user.email_verified:
                # Повторная отправка письма
                uid = urlsafe_base64_encode(force_bytes(existing_user.pk))
                token = default_token_generator.make_token(existing_user)

                verify_url = request.build_absolute_uri(
                    reverse('users:verify_email', kwargs={'uidb64': uid, 'token': token})
                )
                verify_url = re.sub(r'[\u200b\u200c\u200d\u2060\u00ad\ufeff]', '', verify_url)

                subject = _("Подтвердите ваш email")
                message = render_to_string('emails/email_verification_body.txt', {
                    'user': existing_user,
                    'verify_url': verify_url,
                })

                send_mail(
                    subject,
                    message,
                    from_email=None,
                    recipient_list=[existing_user.email],
                    fail_silently=False,
                )

                messages.info(
                    request,
                    _("На этот email уже отправлена ссылка для подтверждения. Проверьте почту."),
                    extra_tags='users'
                )
                return redirect('users:register')
            else:
                # Аккаунт уже подтверждён — ошибка
                messages.error(
                    request,
                    _("Пользователь с таким email уже зарегистрирован и подтверждён."),
                    extra_tags='users'
                )
                return render(request, 'users/register.html', {'form': form})

        # Нового пользователя нет — создаём
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.email_verified = False
            user.save()


            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            verify_url = request.build_absolute_uri(
                reverse('users:verify_email', kwargs={'uidb64': uid, 'token': token})
            )
            verify_url = re.sub(r'[\u200b\u200c\u200d\u2060\u00ad\ufeff]', '', verify_url)

            subject = _("Подтвердите ваш email")
            message = render_to_string('emails/email_verification_body.txt', {
                'user': user,
                'verify_url': verify_url,
            })

            send_mail(
                subject,
                message,
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False,
            )


            messages.success(
                request,
                _("Регистрация завершена. Пожалуйста, проверьте почту и подтвердите адрес."),
                extra_tags='users'
            )
            return redirect('users:register')

    else:
        form = CustomUserCreationForm()

    return render(request, 'users/register.html', {'form': form})


def verify_email_view(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = get_object_or_404(User, pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.email_verified = True
        user.save()
        login(request, user)
        messages.success(
            request,
            _("Ваш email подтверждён. Добро пожаловать!"),
            extra_tags='users'
        )
        return redirect('home')
    else:
        messages.error(
            request,
            _("Ссылка недействительна или устарела. Зарегистрируйтесь снова."),
            extra_tags='users'
        )
        return redirect('users:register')


def login_view(request):
    storage = messages.get_messages(request)
    for message in storage:
        pass
    request.session.pop('messages', None)

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, _("Вы успешно вошли в систему."), extra_tags='users')
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, _("Неверный email или пароль."), extra_tags='users')
        else:
            messages.error(request, _("Неверный email или пароль."), extra_tags='users')
    else:
        form = CustomAuthenticationForm()

    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, _("Вы вышли из системы."), extra_tags='users')
    return redirect('home')



