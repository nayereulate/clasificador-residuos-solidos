from django.contrib import admin
from .models import EntradaHistorial


@admin.register(EntradaHistorial)
class EntradaHistorialAdmin(admin.ModelAdmin):
    list_display    = ('fecha', 'usuario', 'accion', 'modulo', 'descripcion', 'ip_address')
    list_filter     = ('accion', 'modulo')
    search_fields   = ('descripcion', 'usuario__username')
    readonly_fields = ('fecha', 'usuario', 'accion', 'modulo', 'descripcion',
                       'objeto_id', 'objeto_tipo', 'ip_address')
    ordering        = ['-fecha']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
