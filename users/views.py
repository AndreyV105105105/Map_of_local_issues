from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from .forms import CustomUserCreationForm, CustomAuthenticationForm


@login_required
def profile_view(request):
    return render(request, 'users/profile.html')


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _("Registration successful! Welcome to the platform."))
            return redirect('home')
        else:
            messages.error(request, _("Please correct the errors below."))
    else:
        form = CustomUserCreationForm()

    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, _("You are now logged in."))
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, _("Invalid email or password."))
        else:
            messages.error(request, _("Invalid email or password."))
    else:
        form = CustomAuthenticationForm()

    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, _("You have been logged out."))
    return redirect('home')
