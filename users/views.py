import re
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Sum, Subquery, OuterRef, Case, When, Value, \
    BooleanField  # ← добавил Case, When, Value, BooleanField
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _

from issues.models import Issue, Vote, Comment, IssuePhoto
from django.db.models import Prefetch
from .forms import CustomUserCreationForm, CustomAuthenticationForm, CustomSetPasswordForm

User = get_user_model()


@login_required
def profile_view(request):
    issues_count = Issue.objects.filter(reporter=request.user).count()
    if request.user.role == 'official':
        issues_count = Issue.objects.filter(assigned_to=request.user).count()

    return render(request, 'users/profile.html', {
        'issues_count': issues_count
    })


@login_required
def user_issues_view(request):
    user = request.user

    # Подзапрос для текущего голоса пользователя по обращению
    user_vote_subq = Vote.objects.filter(
        issue=OuterRef('pk'),
        user=user
    ).values('value')[:1]

    # Базовый queryset со всеми нужными аннотациями
    base_qs = Issue.objects.select_related('reporter', 'assigned_to').prefetch_related(
        Prefetch('photos', queryset=IssuePhoto.objects.order_by('id'))
    ).annotate(
        vote_rating=Sum('votes__value', default=0),
        user_vote=Subquery(user_vote_subq),
        user_has_upvoted=Case(
            When(user_vote=1, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        ),
        user_has_downvoted=Case(
            When(user_vote=-1, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    )

    if user.role == 'citizen':
        issues = base_qs.filter(reporter=user).order_by('-created_at')
        context = {'issues': issues, 'is_citizen': True}
    else:  # official
        issues_in_progress = base_qs.filter(assigned_to=user, status='IN_PROGRESS').order_by('-updated_at')
        issues_resolved = base_qs.filter(assigned_to=user, status='RESOLVED').order_by('-resolved_at')
        context = {
            'issues_in_progress': issues_in_progress,
            'issues_resolved': issues_resolved,
            'is_official': True
        }

    return render(request, 'users/my_issues.html', context)


@login_required
def user_profile_view(request, user_id):
    """
    Просмотр профиля другого пользователя.
    Показывает все проблемы, которые пользователь создал или взял в работу,
    а также статистику и комментарии.
    """
    profile_user = get_object_or_404(User, id=user_id)
    current_user = request.user

    # Подзапрос для текущего голоса пользователя по обращению
    user_vote_subq = Vote.objects.filter(
        issue=OuterRef('pk'),
        user=current_user
    ).values('value')[:1]

    # Базовый queryset со всеми нужными аннотациями
    base_qs = Issue.objects.select_related('reporter', 'assigned_to').prefetch_related(
        Prefetch('photos', queryset=IssuePhoto.objects.order_by('id'))
    ).annotate(
        vote_rating=Sum('votes__value', default=0),
        user_vote=Subquery(user_vote_subq),
        user_has_upvoted=Case(
            When(user_vote=1, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        ),
        user_has_downvoted=Case(
            When(user_vote=-1, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    )

    # Статистика
    if profile_user.role == 'citizen':
        # Для граждан показываем созданные проблемы
        all_issues_for_stats = Issue.objects.filter(reporter=profile_user)
        issues = base_qs.filter(reporter=profile_user).order_by('-created_at')
        
        stats = {
            'total_created': all_issues_for_stats.count(),
            'open': all_issues_for_stats.filter(status=Issue.STATUS_OPEN).count(),
            'in_progress': all_issues_for_stats.filter(status=Issue.STATUS_IN_PROGRESS).count(),
            'resolved': all_issues_for_stats.filter(status=Issue.STATUS_RESOLVED).count(),
            'total_comments': Comment.objects.filter(author=profile_user).count(),
        }
        
        context = {
            'profile_user': profile_user,
            'issues': issues,
            'is_citizen': True,
            'stats': stats,
            'is_own_profile': profile_user == current_user,
        }
    else:  # official
        # Для официальных лиц показываем проблемы, которые они взяли в работу
        issues_in_progress = base_qs.filter(
            assigned_to=profile_user, 
            status=Issue.STATUS_IN_PROGRESS
        ).order_by('-updated_at')
        issues_resolved = base_qs.filter(
            assigned_to=profile_user, 
            status=Issue.STATUS_RESOLVED
        ).order_by('-resolved_at')
        
        all_assigned_for_stats = Issue.objects.filter(assigned_to=profile_user)
        
        stats = {
            'total_assigned': all_assigned_for_stats.count(),
            'in_progress': all_assigned_for_stats.filter(status=Issue.STATUS_IN_PROGRESS).count(),
            'resolved': all_assigned_for_stats.filter(status=Issue.STATUS_RESOLVED).count(),
            'total_comments': Comment.objects.filter(author=profile_user).count(),
        }
        
        context = {
            'profile_user': profile_user,
            'issues_in_progress': issues_in_progress,
            'issues_resolved': issues_resolved,
            'is_official': True,
            'stats': stats,
            'is_own_profile': profile_user == current_user,
        }

    return render(request, 'users/user_profile.html', context)


def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        # Проверяем, есть ли уже пользователь с таким email
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
