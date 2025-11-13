from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.db.models import Prefetch
from django.shortcuts import render, redirect, get_object_or_404

from .constants import ISSUE_CATEGORIES, ISSUE_CATEGORY_CHOICES
from .models import Issue, IssuePhoto


@login_required
def map_view(request):
    """
    Отображает карту со всеми обращениями.
    Доступно всем авторизованным пользователям.
    """
    # Используем prefetch_related для оптимизации запросов к фотографиям
    issues = Issue.objects.select_related('reporter').prefetch_related('photos').all()
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

    if request.method == 'POST':
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
                messages.warning(request, f"Максимум {max_photos} фото. Лишние игнорируются.")
                photos = photos[:max_photos]

            for photo in photos:
                # Валидация файла (размер, формат — формат уже в модели, но размер здесь)
                if photo.size > 5 * 1024 * 1024:  # >5MB
                    messages.warning(request, f"Файл {photo.name} слишком большой. Игнорируется.")
                    continue
                if not photo.content_type.startswith('image/'):
                    messages.warning(request, f"Файл {photo.name} не изображение. Игнорируется.")
                    continue

                IssuePhoto.objects.create(issue=issue, image=photo)

            messages.success(request, "Ваше обращение успешно зарегистрировано!")
        except Exception as e:
            messages.error(request, "Ошибка при сохранении обращения. Попробуйте позже.")
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
        # Сохраняем информацию для сообщения перед удалением
        title = issue.title
        # Удаляем связанные фотографии (они удалятся автоматически при каскадном удалении)
        issue.delete()
        messages.success(request, f"Обращение «{title}» успешно удалено.")
        return redirect('issues:map')

    # Если GET (кто-то вручную ввёл URL) — не удаляем, а редиректим
    messages.warning(request, "Метод не поддерживается. Используйте кнопку «Удалить».")
    return redirect('issues:map')


@login_required
def issue_detail(request, pk):
    # Получаем проблему с предзагрузкой связанных фотографий для оптимизации запросов
    issue = get_object_or_404(Issue.objects.prefetch_related(
        Prefetch('photos', queryset=IssuePhoto.objects.order_by('id'))
    ), pk=pk)
    return render(request, 'issues/issue_detail.html', {'issue': issue})
