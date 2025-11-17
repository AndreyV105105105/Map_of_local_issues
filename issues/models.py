from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models
from django.core.validators import FileExtensionValidator
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .constants import ISSUE_CATEGORY_CHOICES

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Issue(models.Model):
    STATUS_OPEN = 'OPEN'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_RESOLVED = 'RESOLVED'
    STATUS_CHOICES = [
        (STATUS_OPEN, _('Открыто')),
        (STATUS_IN_PROGRESS, _('В работе')),
        (STATUS_RESOLVED, _('Решено')),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.PointField(srid=4326)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        db_index=True
    )
    category = models.CharField(
        max_length=20,
        choices=ISSUE_CATEGORY_CHOICES,
        db_index=True,
        default='roads'
    )
    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reported_issues'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_issues',
        help_text="Official assigned to resolve this issue"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        permissions = [
            ('can_resolve_issue', 'Can mark issue as resolved'),
            ('can_assign_issue', 'Can assign issues to officials'),
            ('can_view_all_issues', 'Can see all issues regardless of status'),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if self.status == self.STATUS_RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def rating(self):
        """
        Возвращает текущий рейтинг (сумму голосов).
        Если объект аннотирован через _rating — использует его (быстро).
        Иначе — делает запрос к БД (медленно, fallback).
        """
        if hasattr(self, '_rating'):
            return self._rating
        # fallback (например, при вызове issue.rating вне аннотированного QuerySet)
        return self.votes.aggregate(models.Sum('value'))['value__sum'] or 0


class IssuePhoto(models.Model):
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    image = models.ImageField(
        upload_to='issue_photos/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.issue.title}"


class Vote(models.Model):
    VOTE_UP = 1
    VOTE_DOWN = -1
    VOTE_CHOICES = (
        (VOTE_UP, _('За')),
        (VOTE_DOWN, _('Против')),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь')
    )
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name=_('Обращение')
    )
    value = models.SmallIntegerField(
        choices=VOTE_CHOICES,
        verbose_name=_('Голос')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Голос')
        verbose_name_plural = _('Голоса')
        unique_together = ('user', 'issue')

    def __str__(self):
        user_repr = self.user.email if self.user and self.user.email else f"user_{self.user_id or '?'}"
        issue_repr = self.issue.title if self.issue and self.issue.title else f"issue_{self.issue_id or '?'}"
        value_repr = self.get_value_display()
        return f"{user_repr} — {value_repr} — {issue_repr}"


class Comment(models.Model):
    issue = models.ForeignKey(
        'Issue',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Обращение"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='issue_comments',
        verbose_name="Автор"
    )
    text = models.TextField(
        verbose_name="Комментарий",
        help_text="Введите ваш комментарий"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

    def __str__(self):
        return f"Комментарий от {self.author.get_full_name()} к обращению {self.issue.id}"
