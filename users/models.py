# users/models.py
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "official")

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        if "username" not in extra_fields:
            extra_fields["username"] = email

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    email = models.EmailField(_('email address'), unique=True, blank=False)
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        help_text=_("Optional. Used for legacy systems.")
    )
    ROLE_CHOICES = [
        ('citizen', _('Гражданин')),
        ('official', _('Официальное лицо')),
    ]
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='citizen',
        help_text=_("Citizens submit issues; officials manage them")
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='user_profiles/', blank=True, null=True)
    patronymic = models.CharField(
        _("Отчество"),
        max_length=150,
        blank=True,
        help_text=_("Необязательно")
    )

    # 🔑 ПОДТВЕРЖДЕНИЕ EMAIL
    email_verified = models.BooleanField(
        _("Email подтверждён"),
        default=False,
        help_text=_("Указывает, подтверждён ли email пользователя.")
    )
    verification_token = models.UUIDField(
        _("Токен подтверждения"),
        default=uuid.uuid4,
        editable=False
    )
    verification_token_created = models.DateTimeField(
        _("Время создания токена"),
        default=timezone.now
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def get_full_name(self):
        parts = [self.last_name, self.first_name]
        if self.patronymic:
            parts.append(self.patronymic)
        full = " ".join(filter(None, parts)).strip()
        return full or self.email

    def __str__(self):
        return self.get_full_name()




