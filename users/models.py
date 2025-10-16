from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    email = models.EmailField(_('email address'), blank=False)

    # Role field (citizen/official)
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

    # Phone number for citizens
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("For citizen contact info")
    )

    # Department for officials
    department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("City department (e.g., 'Public Works') for officials")
    )

    # Profile picture
    profile_picture = models.ImageField(
        upload_to='user_profiles/',
        blank=True,
        null=True
    )


    def __str__(self):
        return self.username