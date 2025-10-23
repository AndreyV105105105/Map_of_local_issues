from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


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
        ('citizen', 'Citizen'),
        ('official', 'Official'),
    ]
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='citizen',
        help_text=_("Citizens submit issues; officials manage them")
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("For citizen contact info")
    )

    department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("City department (e.g., 'Public Works') for officials")
    )

    profile_picture = models.ImageField(
        upload_to='user_profiles/',
        blank=True,
        null=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        if not self.username and self.email:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email