from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render


class ProfileForm(forms.ModelForm):
    """Editable account details that are safe for a user to change themselves."""

    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'email')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    form = UserCreationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('dashboard:home')

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    form = ProfileForm(
        request.POST if request.method == 'POST' else None,
        instance=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your profile has been updated.')
        return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {'form': form})
