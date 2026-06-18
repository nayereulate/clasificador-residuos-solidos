from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Usuario


class UsuarioCrearForm(UserCreationForm):
    class Meta:
        model  = Usuario
        fields = ('username', 'first_name', 'last_name', 'email',
                  'rol', 'departamento', 'telefono', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['rol'].widget.attrs.update({'class': 'form-select'})


class UsuarioEditarForm(forms.ModelForm):
    class Meta:
        model  = Usuario
        fields = ('first_name', 'last_name', 'email',
                  'rol', 'departamento', 'telefono', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['rol'].widget.attrs.update({'class': 'form-select'})


class PerfilForm(forms.ModelForm):
    class Meta:
        model  = Usuario
        fields = ('first_name', 'last_name', 'email', 'departamento', 'telefono')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
