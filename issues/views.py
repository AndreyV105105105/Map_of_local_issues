import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.contrib.gis.geos import Point
from django.db.models import Q, Prefetch, Case, When, IntegerField, Sum, BooleanField, Value as V, OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .constants import ISSUE_CATEGORIES, ISSUE_CATEGORY_CHOICES
from .forms import CommentForm
from .models import Comment, Issue, IssuePhoto, Vote
from .modules.geocoding import geocode_address, reverse_geocode, search_address

logger = logging.getLogger(__name__)


@login_required
def issue_detail(request, pk):
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
        'comment_form': comment_form,
        'status_choices': Issue.STATUS_CHOICES,
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
    if request.user.role != 'citizen':
        messages.error(request, "Только граждане могут сообщать о проблемах.", extra_tags='issues')
        return redirect('issues:map')

    # --- Инициализация: поддержка pre-fill из GET (карта → кнопка «Сообщить»)
    initial = {
        'title': '',
        'description': '',
        'category': '',
        'address': '',
        'lat': '',
        'lon': '',
    }

    if request.method == 'GET':
        # Получаем данные из URL (lat, lon, address)
        lat = request.GET.get('lat')
        lon = request.GET.get('lon')
        address = request.GET.get('address', '').strip()

        if lat and lon:
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                initial.update(lat=f"{lat_f:.6f}", lon=f"{lon_f:.6f}")
                # Обратное геокодирование для заполнения адреса (но не для изменения координат!)
                if not address:
                    address = reverse_geocode(lat_f, lon_f) or f"Координаты: {lat_f:.6f}, {lon_f:.6f}"
                initial['address'] = address
            except (ValueError, TypeError):
                pass
        # Передаём в шаблон
        return render(request, 'issues/create_issue.html', {
            'categories': ISSUE_CATEGORY_CHOICES,
            'initial': initial,
        })

    # --- POST: обработка формы
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        address = request.POST.get('address', '').strip()
        lat = request.POST.get('lat', '').strip()
        lon = request.POST.get('lon', '').strip()

        # Валидация обязательных полей
        if not all([title, description, category]):
            messages.error(request, "Все поля (название, описание, категория) обязательны.", extra_tags='issues')
            return render(request, 'issues/create_issue.html', {
                'categories': ISSUE_CATEGORY_CHOICES,
                'initial': request.POST.dict(),
            })

        if category not in dict(ISSUE_CATEGORY_CHOICES):
            messages.error(request, "Выбрана недопустимая категория.", extra_tags='issues')
            return render(request, 'issues/create_issue.html', {
                'categories': ISSUE_CATEGORY_CHOICES,
                'initial': request.POST.dict(),
            })

        # --- Определение координат и адреса: ПРИОРИТЕТ — РУЧНЫЕ КООРДИНАТЫ!
        lat_f = lon_f = None
        address_to_save = address

        try:
            # Приоритет 1: координаты из формы (точка клика)
            if lat and lon:
                lat_f = float(lat)
                lon_f = float(lon)
                if not (-90 <= lat_f <= 90) or not (-180 <= lon_f <= 180):
                    raise ValueError("Координаты вне допустимого диапазона")

                # Только для отображения — получаем адрес по координатам (но не перезаписываем lat/lon!)
                if not address_to_save.strip():
                    address_to_save = reverse_geocode(lat_f, lon_f) or f"Координаты: {lat_f:.6f}, {lon_f:.6f}"

            # Приоритет 2: если координат нет — геокодируем адрес
            elif address:
                result = geocode_address(address)
                if result:
                    display_name, point = result
                    lat_f, lon_f = point.y, point.x
                    address_to_save = display_name
                else:
                    messages.error(request, "Не удалось найти адрес. Проверьте написание.", extra_tags='issues')
                    return render(request, 'issues/create_issue.html', {
                        'categories': ISSUE_CATEGORY_CHOICES,
                        'initial': request.POST.dict(),
                    })
            else:
                messages.error(request, "Укажите либо адрес, либо координаты.", extra_tags='issues')
                return render(request, 'issues/create_issue.html', {
                    'categories': ISSUE_CATEGORY_CHOICES,
                    'initial': request.POST.dict(),
                })

        except (ValueError, TypeError) as e:
            logger.info(f"Coordinate parsing error: {e}")
            messages.error(request, "Некорректные координаты.", extra_tags='issues')
            return render(request, 'issues/create_issue.html', {
                'categories': ISSUE_CATEGORY_CHOICES,
                'initial': request.POST.dict(),
            })

        # --- Сохранение
        try:
            issue = Issue.objects.create(
                title=title,
                description=description,
                category=category,
                location=Point(lon_f, lat_f, srid=4326),  # ← ТОЧНЫЕ КООРДИНАТЫ КЛИКА!
                address=address_to_save,  # ← Адрес для отображения
                reporter=request.user,
            )

            # Фото
            photos = request.FILES.getlist('images')
            max_photos = 5
            if len(photos) > max_photos:
                messages.warning(request, f"Максимум {max_photos} фото. Лишние игнорируются.", extra_tags='issues')
                photos = photos[:max_photos]

            for photo in photos:
                if photo.size > 5 * 1024 * 1024:
                    messages.warning(request, f"Файл {photo.name} слишком большой. Игнорируется.", extra_tags='issues')
                    continue
                if not photo.content_type.startswith('image/'):
                    messages.warning(request, f"Файл {photo.name} не изображение. Игнорируется.", extra_tags='issues')
                    continue
                IssuePhoto.objects.create(issue=issue, image=photo)

            messages.success(request, "Ваше обращение успешно зарегистрировано!", extra_tags='issues')
            return redirect('issues:map')

        except Exception as e:
            logger.info(f"Error creating issue: {e}")
            messages.error(request, "Ошибка при сохранении обращения. Попробуйте позже.", extra_tags='issues')
            return render(request, 'issues/create_issue.html', {
                'categories': ISSUE_CATEGORY_CHOICES,
                'initial': request.POST.dict(),
            })


@login_required
def update_issue_status(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)

    if request.user.role != 'official':
        messages.error(request, _("Только должностные лица могут менять статус."))
        return redirect('issues:issue_detail', pk=issue_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status not in dict(Issue.STATUS_CHOICES):
            messages.error(request, _("Неверный статус."))
            return redirect('issues:issue_detail', pk=issue_id)

        old_status = issue.status
        issue.status = new_status

        if new_status == Issue.STATUS_IN_PROGRESS:
            issue.assigned_to = request.user

        if new_status == Issue.STATUS_RESOLVED and old_status != Issue.STATUS_RESOLVED:
            issue.resolved_at = timezone.now()

        issue.save()
        messages.success(request, _("Статус успешно обновлён."))

    return redirect('issues:issue_detail', pk=issue_id)


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

    if vote_value == '0':
        # Удаляем голос, если есть
        deleted,  _ignored = Vote.objects.filter(user=request.user, issue=issue).delete()
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


@method_decorator(login_required, name='dispatch')
class GeocodeAPIView(View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        if not q:
            return JsonResponse({"error": "q required"}, status=400)

        result = geocode_address(q)
        if result:
            display_name, point = result
            return JsonResponse({
                "address": display_name,
                "lat": point.y,
                "lon": point.x,
            })
        return JsonResponse({"error": "Адрес не найден"}, status=404)


@method_decorator(login_required, name='dispatch')
class ReverseGeocodeAPIView(View):
    def get(self, request):
        try:
            lat = float(request.GET.get("lat"))
            lon = float(request.GET.get("lon"))
        except (TypeError, ValueError):
            return JsonResponse({"error": "lat/lon required and must be numeric"}, status=400)

        address = reverse_geocode(lat, lon)
        if address:
            return JsonResponse({"address": address})
        return JsonResponse({"error": "Не удалось определить адрес"}, status=404)


@method_decorator(login_required, name='dispatch')
class SearchAddressAPIView(View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        if len(q) < 2:  # минимум 2 символа
            return JsonResponse({"results": []})

        results = search_address(q, limit=5)
        return JsonResponse({"results": results})
