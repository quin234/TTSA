import os

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
        # Enforce Django's password validators during registration
        super()._post_clean()
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

    ALLOWED_AVATAR_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if not avatar or not isinstance(avatar, UploadedFile):
            return avatar

        ext = os.path.splitext(avatar.name)[1].lower()
        if ext not in self.ALLOWED_AVATAR_EXTENSIONS:
            raise ValidationError(
                'Unsupported file type. Please upload a JPG, PNG, WEBP, or GIF image.'
            )

        if avatar.size > MAX_AVATAR_SIZE:
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


class AdminPlayerCreationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(max_length=128, required=True, widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'placeholder': 'Email (optional)'}))
    id_number = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'placeholder': 'ID Number/Passport (optional)'}))
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'placeholder': 'Phone Number (optional)'}))
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))

    class Meta:
        model = PlayerProfile
        fields = []

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            existing_user = User.objects.filter(username=username).first()
            raise forms.ValidationError(f'Username already exists. User: {existing_user.username}')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            existing_user = User.objects.filter(email=email).first()
            raise forms.ValidationError(f'Email already exists. User: {existing_user.username}')
        return email

    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number')
        if id_number and PlayerProfile.objects.filter(id_number=id_number).exists():
            existing_profile = PlayerProfile.objects.filter(id_number=id_number).first()
            raise forms.ValidationError(f'ID Number/Passport already exists. User: {existing_profile.user.username}')
        return id_number

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and PlayerProfile.objects.filter(phone_number=phone_number).exists():
            existing_profile = PlayerProfile.objects.filter(phone_number=phone_number).first()
            raise forms.ValidationError(f'Phone number already exists. User: {existing_profile.user.username}')
        return phone_number

    def save(self, commit=True):
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']
        email = self.cleaned_data.get('email', '')
        first_name = self.cleaned_data.get('first_name', '')
        last_name = self.cleaned_data.get('last_name', '')
        id_number = self.cleaned_data.get('id_number', '')
        phone_number = self.cleaned_data.get('phone_number', '')

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role='player'
        )

        # Use get_or_create to handle existing profiles gracefully
        profile, created = PlayerProfile.objects.get_or_create(
            user=user,
            defaults={
                'id_number': id_number,
                'phone_number': phone_number
            }
        )

        # Update the profile if it already existed with new data
        if not created:
            profile.id_number = id_number
            profile.phone_number = phone_number
            profile.save()

        return profile


class AdminPlayerEditForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'placeholder': 'Email (optional)'}))
    id_number = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'placeholder': 'ID Number/Passport (optional)'}))
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'placeholder': 'Phone Number (optional)'}))
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    rating = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'placeholder': 'Rating'}))

    class Meta:
        model = PlayerProfile
        fields = []

    def __init__(self, *args, **kwargs):
        self.player_instance = kwargs.pop('player_instance', None)
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if self.player_instance and username != self.player_instance.username:
            if User.objects.filter(username=username).exists():
                existing_user = User.objects.filter(username=username).first()
                raise forms.ValidationError(f'Username already exists. User: {existing_user.username}')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and self.player_instance and email != self.player_instance.email:
            if User.objects.filter(email=email).exists():
                existing_user = User.objects.filter(email=email).first()
                raise forms.ValidationError(f'Email already exists. User: {existing_user.username}')
        return email

    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number')
        if id_number and self.player_instance and id_number != self.player_instance.playerprofile.id_number:
            if PlayerProfile.objects.filter(id_number=id_number).exists():
                existing_profile = PlayerProfile.objects.filter(id_number=id_number).first()
                raise forms.ValidationError(f'ID Number/Passport already exists. User: {existing_profile.user.username}')
        return id_number

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and self.player_instance and phone_number != self.player_instance.playerprofile.phone_number:
            if PlayerProfile.objects.filter(phone_number=phone_number).exists():
                existing_profile = PlayerProfile.objects.filter(phone_number=phone_number).first()
                raise forms.ValidationError(f'Phone number already exists. User: {existing_profile.user.username}')
        return phone_number

    def save(self, commit=True):
        if not self.player_instance:
            raise ValueError('player_instance is required for editing')

        username = self.cleaned_data['username']
        email = self.cleaned_data.get('email', '')
        first_name = self.cleaned_data.get('first_name', '')
        last_name = self.cleaned_data.get('last_name', '')
        id_number = self.cleaned_data.get('id_number', '')
        phone_number = self.cleaned_data.get('phone_number', '')
        rating = self.cleaned_data.get('rating', None)

        # Update user fields
        self.player_instance.username = username
        self.player_instance.email = email
        self.player_instance.first_name = first_name
        self.player_instance.last_name = last_name
        self.player_instance.save()

        # Update profile fields
        profile = self.player_instance.playerprofile
        profile.id_number = id_number
        profile.phone_number = phone_number
        if rating is not None:
            profile.rating = rating
        profile.save()

        return profile
