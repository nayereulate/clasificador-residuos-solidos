from django.conf import settings
from django.db import models


class EntradaHistorial(models.Model):
    ACCIONES = [
        ('ANALIZAR',  'Analizar imagen'),
        ('PROCESAR',  'Procesar residuo'),
        ('EXPORTAR',  'Exportar datos'),
        ('CREAR',     'Crear registro'),
        ('EDITAR',    'Editar registro'),
        ('ELIMINAR',  'Eliminar registro'),
        ('LOGIN',     'Iniciar sesión'),
        ('LOGOUT',    'Cerrar sesión'),
        ('SISTEMA',   'Evento del sistema'),
    ]

    MODULOS = [
        ('clasificacion',  'Detección IA'),
        ('administracion', 'Administración'),
        ('historial',      'Historial'),
        ('reportes',       'Reportes'),
        ('recoleccion',    'Recolección'),
        ('usuarios',       'Usuarios'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='historial_entradas',
        verbose_name='Usuario',
    )
    accion      = models.CharField(max_length=20, choices=ACCIONES, verbose_name='Acción')
    modulo      = models.CharField(max_length=30, choices=MODULOS,  verbose_name='Módulo')
    descripcion = models.TextField(verbose_name='Descripción')
    objeto_id   = models.IntegerField(null=True, blank=True, verbose_name='ID objeto')
    objeto_tipo = models.CharField(max_length=100, blank=True, verbose_name='Tipo objeto')
    ip_address  = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')
    fecha       = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')

    class Meta:
        verbose_name          = 'Entrada de Historial'
        verbose_name_plural   = 'Entradas de Historial'
        ordering              = ['-fecha']

    def __str__(self):
        return f"{self.get_accion_display()} – {self.get_modulo_display()} ({self.fecha:%d/%m/%Y %H:%M})"
