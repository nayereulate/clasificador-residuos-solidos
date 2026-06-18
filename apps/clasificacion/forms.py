from django import forms

from .models import Residuo


class ResiduoForm(forms.ModelForm):
    class Meta:
        model = Residuo
        fields = ["imagen"]
        labels = {
            "imagen": "Seleccionar imagen"
        }
        widgets = {
            "imagen": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*"
                }
            )
        }