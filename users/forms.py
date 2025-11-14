from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        label=_("Электронная почта"),
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    # Добавлены ФИО
    last_name = forms.CharField(
        label=_("Фамилия"),
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        label=_("Имя"),
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    patronymic = forms.CharField(
        label=_("Отчество"),
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text=_("Если есть")
    )

    password1 = forms.CharField(
        label=_("Пароль"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=_("Пароль должен содержать не менее 8 символов.")
    )
    password2 = forms.CharField(
        label=_("Подтверждение пароля"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        label=_("Роль"),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        label=_("Номер телефона"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = (
            'email', 'last_name', 'first_name', 'patronymic',
            'role', 'phone_number', 'password1', 'password2'
        )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Эта электронная почта уже используется."))
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Пароли не совпадают."))
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.patronymic = self.cleaned_data.get("patronymic", "")
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("Электронная почта"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autofocus': True})
    )
    password = forms.CharField(
        label=_("Пароль"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    error_messages = {
        'invalid_login': _(
            "Пожалуйста, введите правильную электронную почту и пароль. Учтите, что оба поля чувствительны к регистру."
        ),
        'inactive': _("Эта учетная запись неактивна."),
    }