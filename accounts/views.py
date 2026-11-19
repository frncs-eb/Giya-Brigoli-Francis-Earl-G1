from django import forms
from django.contrib.auth import authenticate
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Email address', widget=forms.EmailInput(attrs={
        'autocomplete': 'email', 'placeholder': 'name@example.com',
    }))

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if email and password:
            user_model = get_user_model()
            user = user_model.objects.filter(email__iexact=email).first()
            username = user.get_username() if user else email
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=150, label='First Name', widget=forms.TextInput(attrs={
        'autocomplete': 'given-name', 'placeholder': 'Enter your first name',
    }))
    last_name = forms.CharField(max_length=150, label='Last Name', widget=forms.TextInput(attrs={
        'autocomplete': 'family-name', 'placeholder': 'Enter your last name',
    }))
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={
        'autocomplete': 'email', 'placeholder': 'name@example.com',
    }))
    password = forms.CharField(label='Password', strip=False, widget=forms.PasswordInput(attrs={
        'autocomplete': 'new-password', 'placeholder': 'Create a password',
    }))
    confirm_password = forms.CharField(label='Confirm Password', strip=False, widget=forms.PasswordInput(attrs={
        'autocomplete': 'new-password', 'placeholder': 'Confirm your password',
    }))

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'The passwords do not match.')
        return cleaned_data

    def save(self):
        user_model = get_user_model()
        email = self.cleaned_data['email']
        username = email[:150]
        suffix = 1
        while user_model.objects.filter(username__iexact=username).exists():
            suffix_text = str(suffix)
            username = f'{email[:150 - len(suffix_text)]}{suffix_text}'
            suffix += 1
        return user_model.objects.create_user(
            username=username,
            email=email,
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            password=self.cleaned_data['password'],
        )


class ProfileForm(forms.ModelForm):
    """Editable account details that are safe for a user to change themselves."""

    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'email')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    form = RegisterForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            # A duplicate can still be created between form validation and save.
            form.add_error(None, 'An account with this email already exists.')
        else:
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
