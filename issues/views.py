from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.gis.geos import Point
from .models import Issue, Vote
from .constants import ISSUE_CATEGORIES, ISSUE_CATEGORY_CHOICES
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import IntegrityError, models
from django.db.models import Case, When, IntegerField, Sum, BooleanField, Value as V
from django.utils.translation import gettext as _


@login_required
def map_view(request):
    issues = Issue.objects.select_related('reporter').annotate(
        user_vote=Case(
            When(votes__user=request.user, then='votes__value'),
            default=None,
            output_field=IntegerField()
        ),
        user_has_upvoted=Case(
            When(votes__user=request.user, votes__value=1, then=V(True)),
            default=V(False),
            output_field=models.BooleanField()
        ),
        user_has_downvoted=Case(
            When(votes__user=request.user, votes__value=-1, then=V(True)),
            default=V(False),
            output_field=models.BooleanField()
        ),
        vote_rating=Sum('votes__value', default=0)
    )
    return render(request, 'issues/map.html', {
        'issues': issues,
        'categories': ISSUE_CATEGORIES,
        'user_role': request.user.role,
    })

@login_required
def create_issue(request):
    """
    Создаёт новое обращение.
    Доступно только гражданам (role == 'citizen').
    """
    if request.user.role != 'citizen':
        messages.error(request, "Только граждане могут сообщать о проблемах.")
        return redirect('issues:map')

    if request.method != 'POST':
        # Форма вызывается только через POST из модального окна
        return redirect('issues:map')

    # Получаем данные
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    category = request.POST.get('category', '').strip()
    lat = request.POST.get('lat', '').strip()
    lon = request.POST.get('lon', '').strip()

    # Валидация
    if not all([title, description, category, lat, lon]):
        messages.error(request, "Все поля обязательны для заполнения.")
        return redirect('issues:map')

    if category not in dict(ISSUE_CATEGORY_CHOICES):
        messages.error(request, "Выбрана недопустимая категория.")
        return redirect('issues:map')

    try:
        lat_float = float(lat)
        lon_float = float(lon)
        if not (-90 <= lat_float <= 90):
            raise ValueError("Некорректная широта")
        if not (-180 <= lon_float <= 180):
            raise ValueError("Некорректная долгота")
    except (ValueError, TypeError):
        messages.error(request, "Некорректные координаты.")
        return redirect('issues:map')

    # Сохраняем обращение
    try:
        Issue.objects.create(
            title=title,
            description=description,
            category=category,
            location=Point(lon_float, lat_float, srid=4326),
            reporter=request.user,
        )
        messages.success(request, "Ваше обращение успешно зарегистрировано!")
    except Exception as e:
        messages.error(request, "Ошибка при сохранении обращения. Попробуйте позже.")
        # В продакшене логируйте ошибку: logger.exception(e)

    return redirect('issues:map')


@login_required
def update_issue_status(request, issue_id):
    """
    Обновляет статус обращения.
    Доступно только официальным лицам (role == 'official').
    """
    if request.user.role != 'official':
        messages.error(request, "Только официальные лица могут обрабатывать обращения.")
        return redirect('issues:map')

    issue = get_object_or_404(Issue, id=issue_id)

    if request.method != 'POST':
        return redirect('issues:map')

    new_status = request.POST.get('status')
    valid_statuses = dict(Issue.STATUS_CHOICES).keys()

    if new_status not in valid_statuses:
        messages.error(request, "Недопустимый статус.")
        return redirect('issues:map')

    issue.status = new_status
    issue.save(update_fields=['status', 'updated_at'])
    messages.success(request, f"Статус изменён на «{issue.get_status_display()}».")

    return redirect('issues:map')

@login_required
def delete_issue(request, issue_id):
    if request.user.role != 'official':
        messages.error(request, "Только должностные лица могут удалять обращения.")
        return redirect('issues:map')

    issue = get_object_or_404(Issue, id=issue_id)

    if request.method == 'POST':
        title = issue.title
        issue.delete()
        messages.success(request, f"Обращение «{title}» успешно удалено.")
        return redirect('issues:map')

    # Если GET (кто-то вручную ввёл URL) — не удаляем, а редиректим
    messages.warning(request, "Метод не поддерживается. Используйте кнопку «Удалить».")
    return redirect('issues:map')
from .models import Issue, Vote  # ← критически важно

@login_required
@require_POST
def vote_issue(request, issue_id):
    # Проверка роли
    if request.user.role != 'citizen':
        return JsonResponse({
            'success': False,
            'error': _('Только граждане могут голосовать.')
        }, status=403)

    issue = get_object_or_404(Issue, id=issue_id)
    vote_value = request.POST.get('vote')

    # Обработка: '1' → +1, '-1' → -1, '0' → отмена
    if vote_value == '0':
        # Удаляем голос, если есть
        deleted, _ = Vote.objects.filter(user=request.user, issue=issue).delete()
        user_vote = None
    elif vote_value in ['1', '-1']:
        value = int(vote_value)
        vote, created = Vote.objects.update_or_create(
            user=request.user,
            issue=issue,
            defaults={'value': value}
        )
        user_vote = vote.value
    else:
        return JsonResponse({
            'success': False,
            'error': _('Голос должен быть +1, -1 или 0 (отмена).')
        }, status=400)

    # Вычисляем рейтинг напрямую через агрегацию — быстро и надёжно
    rating = issue.votes.aggregate(rating_sum=Sum('value'))['rating_sum'] or 0

    return JsonResponse({
        'success': True,
        'rating': rating,
        'user_vote': user_vote,  # null, 1 или -1
        'issue_id': issue_id
    })
@login_required
def issue_detail(request, pk):
    issue = Issue.objects.annotate(
        user_vote=Case(
            When(votes__user=request.user, then='votes__value'),
            default=None,
            output_field=IntegerField()
        ),
        user_has_upvoted=Case(
            When(votes__user=request.user, votes__value=1, then=V(True)),
            default=V(False),
            output_field=models.BooleanField()
        ),
        user_has_downvoted=Case(
            When(votes__user=request.user, votes__value=-1, then=V(True)),
            default=V(False),
            output_field=models.BooleanField()
        ),
        vote_rating=Sum('votes__value', default=0)
    ).get(pk=pk)

    return render(request, 'issues/issue_detail.html', {'issue': issue})
