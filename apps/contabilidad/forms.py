from django import forms

from .models import Ingreso, Egreso, CategoriaIngreso, CategoriaEgreso


class IngresoForm(forms.ModelForm):
    class Meta:
        model = Ingreso
        fields = ["tipo", "categoria", "material", "cantidad_kg", "precio_por_kg",
                  "monto_total", "descripcion", "fecha"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "material": forms.TextInput(attrs={"class": "form-control", "placeholder": "Metal, Vidrio, Plástico…"}),
            "cantidad_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "precio_por_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "monto_total": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


class EgresoForm(forms.ModelForm):
    class Meta:
        model = Egreso
        fields = ["concepto", "categoria", "monto", "descripcion", "fecha"]
        widgets = {
            "concepto": forms.TextInput(attrs={"class": "form-control", "placeholder": "Descripción del gasto"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "monto": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
