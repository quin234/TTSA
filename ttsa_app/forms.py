from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from .models import User, PlayerProfile, Message, PlayerPlusApplication


MAX_AVATAR_SIZE = 1024 * 1024  # 1 MB


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def _post_clean(self):
        # Bypass Django's password validators for registrations, allowing simple passwords
        super(forms.ModelForm, self)._post_clean()
        password = self.cleaned_data.get("password2")
        if password:
            self.instance.set_password(password)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = PlayerProfile
        fields = ['avatar', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell us about yourself...'}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and isinstance(avatar, UploadedFile) and avatar.size > MAX_AVATAR_SIZE:
            raise ValidationError(
                f'Avatar must be less than 1 MB. Your file is {avatar.size / (1024 * 1024):.2f} MB.'
            )
        return avatar


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Type your message...'}),
        }


class FriendRequestForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Enter username to add as friend'})
    )


class PlayerPlusApplicationForm(forms.ModelForm):
    class Meta:
        model = PlayerPlusApplication
        fields = ['full_name', 'phone_number', 'additional_info']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'Phone number'}),
            'additional_info': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any additional information'}),
        }
