import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.db.models import Q, Prefetch, Case, When, IntegerField, Sum, BooleanField, Value as V, OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
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
    """Детали обращения"""
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
    Отображает карту со всеми обращениями с возможностью фильтрации
    """
    # Get filter params from GET
    category = request.GET.get('category')
    status = request.GET.get('status')
    search = request.GET.get('search', '').strip()
    sort = request.GET.get('sort', '-created_at')

    # Current user's vote per issue
    user_vote_subq = Vote.objects.filter(
        issue=OuterRef('pk'),
        user=request.user
    ).values('value')[:1]

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

    # Apply filters
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

    # Apply sorting
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

    # AJAX: return partial list only
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'issues/partials/issues_list.html', context)

    return render(request, 'issues/map.html', context)


@login_required
def create_issue(request):
    if request.user.role != 'citizen':
        messages.error(request, _("Только граждане могут сообщать о проблемах."), extra_tags='issues')
        return redirect('issues:map')

    # --- Initialization: support pre-fill from GET
    initial = {
        'title': '',
        'description': '',
        'category': '',
        'address': '',
        'lat': '',
        'lon': '',
    }

    if request.method == 'GET':
        lat = request.GET.get('lat')
        lon = request.GET.get('lon')
        address = request.GET.get('address', '').strip()

        if lat and lon:
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                initial.update(lat=f"{lat_f:.6f}", lon=f"{lon_f:.6f}")
                if not address:
                    address = reverse_geocode(lat_f, lon_f) or f"Координаты: {lat_f:.6f}, {lon_f:.6f}"
                initial['address'] = address
            except (ValueError, TypeError):
                pass
        return render(request, 'issues/create_issue.html', {
            'categories': ISSUE_CATEGORY_CHOICES,
            'initial': initial,
        })

    # POST: form handling
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        address = request.POST.get('address', '').strip()
        lat = request.POST.get('lat', '').strip()
        lon = request.POST.get('lon', '').strip()

        if not all([title, description, category]):
            messages.error(request, _("Все поля (название, описание, категория) обязательны."), extra_tags='issues')
            return render(request, 'issues/create_issue.html', {
                'categories': ISSUE_CATEGORY_CHOICES,
                'initial': request.POST.dict(),
            })

        if category not in dict(ISSUE_CATEGORY_CHOICES):
            messages.error(request, _("Выбрана недопустимая категория."), extra_tags='issues')
            return render(request, 'issues/create_issue.html', {
                'categories': ISSUE_CATEGORY_CHOICES,
                'initial': request.POST.dict(),
            })

        lat_f = lon_f = None
        address_to_save = address

        try:
            if lat and lon:
                lat_f = float(lat)
                lon_f = float(lon)
                if not (-90 <= lat_f <= 90) or not (-180 <= lon_f <= 180):
                    raise ValueError("Координаты вне допустимого диапазона")
                if not address_to_save.strip():
                    address_to_save = reverse_geocode(lat_f, lon_f) or f"Координаты: {lat_f:.6f}, {lon_f:.6f}"
            elif address:
                result = geocode_address(address)
                if result:
                    display_name, point = result
                    lat_f, lon_f = point.y, point.x
                    address_to_save = display_name
                else:
                    messages.error(request, _("Не удалось найти адрес. Проверьте написание."), extra_tags='issues')
                    return render(request, 'issues/create_issue.html', {
                        'categories': ISSUE_CATEGORY_CHOICES,
                        'initial': request.POST.dict(),
                    })
            else:
                messages.error(request, _("Укажите либо адрес, либо координаты."), extra_tags='issues')
                return render(request, 'issues/create_issue.html', {
                    'categories': ISSUE_CATEGORY_CHOICES,
                    'initial': request.POST.dict(),
                })

        except (ValueError, TypeError) as e:
            logger.info(f"Coordinate parsing error: {e}")
            messages.error(request, _("Некорректные координаты."), extra_tags='issues')
            return render(request, 'issues/create_issue.html', {
                'categories': ISSUE_CATEGORY_CHOICES,
                'initial': request.POST.dict(),
            })

        try:
            issue = Issue.objects.create(
                title=title,
                description=description,
                category=category,
                location=Point(lon_f, lat_f, srid=4326),
                address=address_to_save,
                reporter=request.user,
            )

            photos = request.FILES.getlist('images')
            max_photos = 5
            if len(photos) > max_photos:
                messages.warning(request, _(f"Максимум {max_photos} фото. Лишние игнорируются."), extra_tags='issues')
                photos = photos[:max_photos]

            for photo in photos:
                if photo.size > 5 * 1024 * 1024:
                    messages.warning(request, _(f"Файл {photo.name} слишком большой. Игнорируется."), extra_tags='issues')
                    continue
                if not photo.content_type.startswith('image/'):
                    messages.warning(request, _(f"Файл {photo.name} не изображение. Игнорируется."), extra_tags='issues')
                    continue
                IssuePhoto.objects.create(issue=issue, image=photo)

            messages.success(request, _("Ваше обращение успешно зарегистрировано!"), extra_tags='issues')
            return redirect('issues:map')

        except Exception as e:
            logger.info(f"Error creating issue: {e}")
            messages.error(request, _("Ошибка при сохранении обращения. Попробуйте позже."), extra_tags='issues')
            return render(request, 'issues/create_issue.html', {
                'categories': ISSUE_CATEGORY_CHOICES,
                'initial': request.POST.dict(),
            })


@login_required
@require_POST
def update_issue_status(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)

    if request.user.role != 'official':
        messages.error(request, _("У вас нет прав для изменения статуса."))
        return redirect('issues:issue_detail', pk=issue_id)

    if issue.assigned_to and issue.assigned_to != request.user:
        messages.error(
            request,
            _(f"Эта проблема уже взята в работу пользователем {issue.assigned_to.get_full_name()}. Только он может изменить статус.")
        )
        return redirect('issues:issue_detail', pk=issue_id)

    new_status = request.POST.get('status')
    if new_status in dict(Issue.STATUS_CHOICES):
        if new_status == Issue.STATUS_IN_PROGRESS and not issue.assigned_to:
            issue.assigned_to = request.user
        issue.status = new_status
        issue.save()
        messages.success(request, _("Статус обращения успешно обновлён."))
    else:
        messages.error(request, _("Неверный статус."))

    return redirect('issues:issue_detail', pk=issue_id)


@login_required
def delete_issue(request, issue_id):
    if request.user.role != 'official':
        messages.error(request, _("Только должностные лица могут удалять обращения."), extra_tags='issues')
        return redirect('issues:map')

    issue = get_object_or_404(Issue, id=issue_id)

    if request.method == 'POST':
        title = issue.title
        issue.delete()
        messages.success(request, _(f"Обращение «{title}» успешно удалено."), extra_tags='issues')
        return redirect('issues:map')

    messages.warning(request, _("Метод не поддерживается. Используйте кнопку «Удалить»."), extra_tags='issues')
    return redirect('issues:map')


@login_required
@require_POST
def vote_issue(request, issue_id):
    # ✅ Fix: use gettext() for runtime translation in JSON responses
    if request.user.role != 'citizen':
        return JsonResponse({
            'success': False,
            'error': gettext('Только граждане могут голосовать.')
        }, status=403)

    issue = get_object_or_404(Issue, id=issue_id)
    vote_value = request.POST.get('vote')

    if vote_value == '0':
        Vote.objects.filter(user=request.user, issue=issue).delete()
        user_vote = None
    elif vote_value in ['1', '-1']:
        value = int(vote_value)
        Vote.objects.update_or_create(
            user=request.user,
            issue=issue,
            defaults={'value': value}
        )
        user_vote = value
    else:
        return JsonResponse({
            'success': False,
            'error': gettext('Голос должен быть +1, -1 или 0 (отмена).')
        }, status=400)

    rating = issue.votes.aggregate(rating_sum=Sum('value'))['rating_sum'] or 0

    return JsonResponse({
        'success': True,
        'rating': rating,
        'user_vote': user_vote,
        'issue_id': issue_id
    })


@login_required
def get_issues_geojson(request):
    """Возвращает GeoJSON с данными об обращениях для карты с учетом фильтров"""
    category = request.GET.get('category')
    status = request.GET.get('status')
    search = request.GET.get('search', '').strip()

    issues = Issue.objects.select_related('reporter').annotate(
        vote_rating=Sum('votes__value', default=0)
    )

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
            return JsonResponse({"error": gettext("Параметр 'q' обязателен.")}, status=400)

        result = geocode_address(q)
        if result:
            display_name, point = result
            return JsonResponse({
                "address": display_name,
                "lat": point.y,
                "lon": point.x,
            })
        return JsonResponse({"error": gettext("Адрес не найден.")}, status=404)


@method_decorator(login_required, name='dispatch')
class ReverseGeocodeAPIView(View):
    def get(self, request):
        try:
            lat = float(request.GET.get("lat"))
            lon = float(request.GET.get("lon"))
        except (TypeError, ValueError):
            return JsonResponse({
                "error": gettext("Параметры 'lat' и 'lon' обязательны и должны быть числами.")
            }, status=400)

        address = reverse_geocode(lat, lon)
        if address:
            return JsonResponse({"address": address})
        return JsonResponse({"error": gettext("Не удалось определить адрес.")}, status=404)


@method_decorator(login_required, name='dispatch')
class SearchAddressAPIView(View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        if len(q) < 2:
            return JsonResponse({"results": []})

        results = search_address(q, limit=5)
        return JsonResponse({"results": results})