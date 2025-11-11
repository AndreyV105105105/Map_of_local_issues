from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.gis.geos import Point
from .models import Issue
from .constants import ISSUE_CATEGORIES, ISSUE_CATEGORY_CHOICES
from django.conf import settings 


@login_required
def map_view(request):
    """
    Отображает карту со всеми обращениями.
    Доступно всем авторизованным пользователям.
    """
    issues = Issue.objects.select_related('reporter').all()
    return render(request, 'issues/map.html', {
        'issues': issues,
        'categories': ISSUE_CATEGORIES,
        'user_role': request.user.role,
        'JAWG_TOKEN': settings.JAWG_TOKEN,
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
