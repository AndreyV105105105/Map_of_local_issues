from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.db.models import Q, Prefetch, Case, When, IntegerField, Sum, BooleanField, Value as V, OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .constants import ISSUE_CATEGORIES, ISSUE_CATEGORY_CHOICES
from .forms import CommentForm
from .models import Comment
from .models import Issue, IssuePhoto, Vote


@login_required
def issue_detail(request, pk):
    # Add prefetch for comments
    user_vote_subq = Vote.objects.filter(
        issue=OuterRef('pk'),
        user=request.user
    ).values('value')[:1]

    issue = get_object_or_404(
        Issue.objects.prefetch_related(
            Prefetch('photos', queryset=IssuePhoto.objects.order_by('id')),
            Prefetch('comments', queryset=Comment.objects.select_related('author').order_by('-created_at'))
        ).annotate(
            user_vote=Subquery(user_vote_subq, output_field=IntegerField()),
            user_has_upvoted=Case(
                When(user_vote=1, then=V(True)),
                default=V(False),
                output_field=BooleanField()
            ),
            user_has_downvoted=Case(
                When(user_vote=-1, then=V(True)),
                default=V(False),
                output_field=BooleanField()
            ),
            vote_rating=Sum('votes__value', default=0)
        ),
        pk=pk
    )

    # Handle comment form - allow both citizens and officials
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.issue = issue
            comment.author = request.user
            comment.save()
            return redirect('issues:issue_detail', pk=issue.pk)
    else:
        comment_form = CommentForm()

    return render(request, 'issues/issue_detail.html', {
        'issue': issue,
        'comment_form': comment_form
    })


@login_required
def map_view(request):
    """
    Отображает карту со всеми обращениями с возможностью фильтрации.
    Доступно всем авторизованным пользователям.
    """
    # Получаем параметры фильтрации из GET-запроса
    category = request.GET.get('category')
    status = request.GET.get('status')
    search = request.GET.get('search', '').strip()
    sort = request.GET.get('sort', '-created_at')  # сортировка по умолчанию

    # Подзапрос: голос текущего пользователя по каждому Issue
    user_vote_subq = Vote.objects.filter(
        issue=OuterRef('pk'),
        user=request.user
    ).values('value')[:1]

    # Базовый QuerySet
    issues = Issue.objects.select_related('reporter').prefetch_related(
        Prefetch('photos', queryset=IssuePhoto.objects.order_by('id'))
    ).annotate(
        user_vote=Subquery(user_vote_subq, output_field=IntegerField()),
        user_has_upvoted=Case(
            When(user_vote=1, then=V(True)),
            default=V(False),
            output_field=BooleanField()
        ),
        user_has_downvoted=Case(
            When(user_vote=-1, then=V(True)),
            default=V(False),
            output_field=BooleanField()
        ),
        vote_rating=Sum('votes__value', default=0)
    )

    # Применяем фильтры
    if category and category in dict(ISSUE_CATEGORY_CHOICES).keys():
        issues = issues.filter(category=category)

    if status and status in dict(Issue.STATUS_CHOICES).keys():
        issues = issues.filter(status=status)

    if search:
        issues = issues.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(reporter__email__icontains=search) |
            Q(reporter__first_name__icontains=search) |
            Q(reporter__last_name__icontains=search)
        )

    # Применяем сортировку
    valid_sort_fields = ['-created_at', 'created_at', '-vote_rating', 'vote_rating', 'title']
    if sort not in valid_sort_fields:
        sort = '-created_at'
    issues = issues.order_by(sort)

    context = {
        'issues': issues,
        'categories': ISSUE_CATEGORIES,
        'user_role': request.user.role,
        'selected_category': category,
        'selected_status': status,
        'search_query': search,
        'selected_sort': sort,
        'status_choices': Issue.STATUS_CHOICES,
    }

    # Если запрос AJAX, возвращаем только список проблем
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'issues/partials/issues_list.html', context)

    return render(request, 'issues/map.html', context)


@login_required
def create_issue(request):
    """
    Создаёт новое обращение.
    Доступно только гражданам (role == 'citizen').
    """
    if request.user.role != 'citizen':
        messages.error(request, "Только граждане могут сообщать о проблемах.", extra_tags='issues')
        return redirect('issues:map')

    if request.method == 'POST':
        # Получаем данные
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        lat = request.POST.get('lat', '').strip()
        lon = request.POST.get('lon', '').strip()

        # Валидация
        if not all([title, description, category, lat, lon]):
            messages.error(request, "Все поля обязательны для заполнения.", extra_tags='issues')
            return redirect('issues:map')

        if category not in dict(ISSUE_CATEGORY_CHOICES):
            messages.error(request, "Выбрана недопустимая категория.", extra_tags='issues')
            return redirect('issues:map')

        try:
            lat_float = float(lat)
            lon_float = float(lon)
            if not (-90 <= lat_float <= 90):
                raise ValueError("Некорректная широта")
            if not (-180 <= lon_float <= 180):
                raise ValueError("Некорректная долгота")
        except (ValueError, TypeError):
            messages.error(request, "Некорректные координаты.", extra_tags='issues')
            return redirect('issues:map')

        # Сохраняем обращение
        try:
            issue = Issue.objects.create(
                title=title,
                description=description,
                category=category,
                location=Point(lon_float, lat_float, srid=4326),
                reporter=request.user,
            )

            # Обработка фото (множественные)
            photos = request.FILES.getlist('images')  # Имя поля в форме — 'images'
            max_photos = 5  # Ограничение
            if len(photos) > max_photos:
                messages.warning(request, f"Максимум {max_photos} фото. Лишние игнорируются.", extra_tags='issues')
                photos = photos[:max_photos]

            for photo in photos:
                # Валидация файла (размер, формат — формат уже в модели, но размер здесь)
                if photo.size > 5 * 1024 * 1024:  # >5MB
                    messages.warning(request, f"Файл {photo.name} слишком большой. Игнорируется., extra_tags='issues'")
                    continue
                if not photo.content_type.startswith('image/'):
                    messages.warning(request, f"Файл {photo.name} не изображение. Игнорируется.", extra_tags='issues')
                    continue

                IssuePhoto.objects.create(issue=issue, image=photo)

            messages.success(request, "Ваше обращение успешно зарегистрировано!", extra_tags='issues')
        except Exception as e:
            messages.error(request, "Ошибка при сохранении обращения. Попробуйте позже.", extra_tags='issues')
            # В продакшене логируйте ошибку: logger.exception(e)

        return redirect('issues:map')

    # Для GET: рендерим форму (добавлено, поскольку шаблон существует)
    return render(request, 'issues/create_issue.html', {
        'categories': ISSUE_CATEGORY_CHOICES,  # Передаем choices для выпадающего списка
    })


@login_required
def update_issue_status(request, issue_id):
    """
    Обновляет статус обращения.
    Доступно только официальным лицам (role == 'official').
    """
    if request.user.role != 'official':
        messages.error(request, "Только официальные лица могут обрабатывать обращения.", extra_tags='issues')
        return redirect('issues:map')

    issue = get_object_or_404(Issue, id=issue_id)

    if request.method != 'POST':
        return redirect('issues:map')

    new_status = request.POST.get('status')
    valid_statuses = dict(Issue.STATUS_CHOICES).keys()

    if new_status not in valid_statuses:
        messages.error(request, "Недопустимый статус.", extra_tags='issues')
        return redirect('issues:map')

    issue.status = new_status
    issue.save(update_fields=['status', 'updated_at'])
    messages.success(request, f"Статус изменён на «{issue.get_status_display()}».", extra_tags='issues')

    return redirect('issues:map')


@login_required
def delete_issue(request, issue_id):
    if request.user.role != 'official':
        messages.error(request, "Только должностные лица могут удалять обращения.", extra_tags='issues')
        return redirect('issues:map')

    issue = get_object_or_404(Issue, id=issue_id)

    if request.method == 'POST':
        # Сохраняем информацию для сообщения перед удалением
        title = issue.title
        # Удаляем связанные фотографии (они удалятся автоматически при каскадном удалении)
        issue.delete()
        messages.success(request, f"Обращение «{title}» успешно удалено.", extra_tags='issues')
        return redirect('issues:map')

    # Если GET (кто-то вручную ввёл URL) — не удаляем, а редиректим
    messages.warning(request, "Метод не поддерживается. Используйте кнопку «Удалить».", extra_tags='issues')
    return redirect('issues:map')


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
def get_issues_geojson(request):
    """
    Возвращает GeoJSON с данными об обращениях для карты с учетом фильтров.
    """
    # Получаем параметры фильтрации
    category = request.GET.get('category')
    status = request.GET.get('status')
    search = request.GET.get('search', '').strip()

    # Базовый QuerySet
    issues = Issue.objects.select_related('reporter').annotate(
        vote_rating=Sum('votes__value', default=0)
    )

    # Применяем фильтры
    if category and category in dict(ISSUE_CATEGORY_CHOICES).keys():
        issues = issues.filter(category=category)

    if status and status in dict(Issue.STATUS_CHOICES).keys():
        issues = issues.filter(status=status)

    if search:
        issues = issues.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(reporter__email__icontains=search) |
            Q(reporter__first_name__icontains=search) |
            Q(reporter__last_name__icontains=search)
        )

    # Формируем GeoJSON
    features = []
    for issue in issues:
        if issue.location:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [issue.location.x, issue.location.y]
                },
                'properties': {
                    'id': issue.id,
                    'title': issue.title,
                    'status': issue.status,
                    'status_display': issue.get_status_display(),
                    'category': issue.category,
                    'category_display': issue.get_category_display(),
                    'vote_rating': issue.vote_rating,
                    'photos_count': issue.photos.count(),
                    'url': reverse('issues:issue_detail', args=[issue.id])
                }
            }
            features.append(feature)

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    return JsonResponse(geojson)
