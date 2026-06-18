from django import forms
from .models import RutaRecoleccion, Zona


class RutaForm(forms.ModelForm):
    class Meta:
        model  = RutaRecoleccion
        fields = ('nombre', 'zona', 'operador', 'fecha_programada',
                  'hora_programada', 'prioridad', 'notas')
        widgets = {
            'fecha_programada': forms.DateInput(attrs={'type': 'date'}),
            'hora_programada':  forms.TimeInput(attrs={'type': 'time'}),
            'notas':            forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.NullBooleanSelect)):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

        # Solo usuarios activos como operadores
        from apps.usuarios.models import Usuario
        self.fields['operador'].queryset = Usuario.objects.filter(is_active=True).order_by('first_name', 'username')
        self.fields['operador'].required = False


class ZonaForm(forms.ModelForm):
    class Meta:
        model  = Zona
        fields = ('nombre', 'descripcion', 'color')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['color'].widget.attrs.update({'class': 'form-select'})
