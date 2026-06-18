from django.contrib import admin
from .models import Zona, RutaRecoleccion


@admin.register(Zona)
class ZonaAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'color', 'descripcion')
    search_fields = ('nombre',)


@admin.register(RutaRecoleccion)
class RutaAdmin(admin.ModelAdmin):
    list_display      = ('nombre', 'zona', 'operador', 'fecha_programada', 'estado', 'prioridad')
    list_filter       = ('estado', 'prioridad', 'zona')
    search_fields     = ('nombre',)
    date_hierarchy    = 'fecha_programada'
    filter_horizontal = ('residuos',)
