from django.conf import settings
from django.db import models


class Zona(models.Model):
    COLOR_CHOICES = [
        ('#1b4332', 'Verde oscuro'),
        ('#1d3557', 'Azul marino'),
        ('#780000', 'Rojo oscuro'),
        ('#7b2d8b', 'Morado'),
        ('#b5451b', 'Naranja oscuro'),
    ]

    nombre      = models.CharField(max_length=100, verbose_name='Nombre')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    color       = models.CharField(max_length=20, default='#1b4332', choices=COLOR_CHOICES,
                                   verbose_name='Color de identificación')
    latitud     = models.FloatField(null=True, blank=True, verbose_name='Latitud')
    longitud    = models.FloatField(null=True, blank=True, verbose_name='Longitud')

    class Meta:
        verbose_name        = 'Zona'
        verbose_name_plural = 'Zonas'
        ordering            = ['nombre']

    def __str__(self):
        return self.nombre


class RutaRecoleccion(models.Model):
    ESTADOS = [
        ('pendiente',   'Pendiente'),
        ('en_proceso',  'En proceso'),
        ('completada',  'Completada'),
        ('cancelada',   'Cancelada'),
    ]

    PRIORIDADES = [
        ('alta',  'Alta'),
        ('media', 'Media'),
        ('baja',  'Baja'),
    ]

    nombre = models.CharField(max_length=200, verbose_name='Nombre de la ruta')
    zona   = models.ForeignKey(
        Zona, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='rutas', verbose_name='Zona',
    )
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rutas_asignadas',
        verbose_name='Operador asignado',
        limit_choices_to={'is_active': True},
    )
    fecha_programada = models.DateField(verbose_name='Fecha programada')
    hora_programada  = models.TimeField(null=True, blank=True, verbose_name='Hora programada')
    estado           = models.CharField(max_length=20, choices=ESTADOS, default='pendiente',
                                        verbose_name='Estado')
    prioridad        = models.CharField(max_length=10, choices=PRIORIDADES, default='media',
                                        verbose_name='Prioridad')
    residuos         = models.ManyToManyField(
        'clasificacion.Residuo',
        blank=True, related_name='rutas', verbose_name='Residuos asignados',
    )
    notas           = models.TextField(blank=True, verbose_name='Notas adicionales')
    fecha_creacion  = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_completada = models.DateTimeField(null=True, blank=True,
                                            verbose_name='Fecha de completado')

    class Meta:
        verbose_name        = 'Ruta de Recolección'
        verbose_name_plural = 'Rutas de Recolección'
        ordering            = ['fecha_programada', 'prioridad']

    def __str__(self):
        return f"{self.nombre} ({self.get_estado_display()}) – {self.fecha_programada}"

    @property
    def total_residuos(self):
        return self.residuos.count()

    @property
    def color_estado(self):
        return {
            'pendiente':  'warning',
            'en_proceso': 'primary',
            'completada': 'success',
            'cancelada':  'danger',
        }.get(self.estado, 'secondary')

    @property
    def color_prioridad(self):
        return {
            'alta':  'danger',
            'media': 'warning',
            'baja':  'success',
        }.get(self.prioridad, 'secondary')
