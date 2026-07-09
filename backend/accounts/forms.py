from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class SignupForm(forms.Form):
    email = forms.EmailField()
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    company_name = forms.CharField(max_length=255, label="Company Name")

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                raise forms.ValidationError(exc.messages)
        return password

    def clean(self):
        cleaned = super().clean()

        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")