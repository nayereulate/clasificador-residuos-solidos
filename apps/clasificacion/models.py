from django.conf import settings
from django.db import models


class Residuo(models.Model):

    imagen = models.ImageField(
        upload_to="residuos/"
    )

    tipo = models.CharField(
        max_length=100,
        blank=True
    )

    categoria = models.CharField(
        max_length=100,
        blank=True
    )

    confianza = models.FloatField(
        default=0
    )

    resultado_json = models.JSONField(
        default=dict,
        blank=True
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.tipo} - {self.categoria}"

class ResultadoAdministracion(models.Model):

    residuo = models.OneToOneField(
        'Residuo',
        on_delete=models.CASCADE,
        related_name='administracion'
    )

    material_predominante = models.CharField(
        max_length=100,
        blank=True
    )

    materiales = models.JSONField(
        default=dict,
        blank=True
    )

    prioridad = models.CharField(
        max_length=50,
        blank=True
    )

    nivel_prioridad = models.IntegerField(
        default=6
    )

    alertas = models.JSONField(
        default=list,
        blank=True
    )

    resultado_grammar = models.JSONField(
        default=dict,
        blank=True
    )

    peso_medio_kg = models.FloatField(
        default=0,
        help_text="Peso medio estimado por el Grammar Engine (kg) para el material predominante"
    )

    fecha_procesado = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Admin #{self.residuo_id} – {self.material_predominante} [{self.prioridad}]"


class ResiduoAceptado(models.Model):
    """Registro de residuos aceptados formalmente por el área de administración."""

    residuo = models.OneToOneField(
        'Residuo',
        on_delete=models.CASCADE,
        related_name='aceptado'
    )

    aceptado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    fecha_aceptacion = models.DateTimeField(auto_now_add=True)

    peso_kg = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Peso estimado del residuo en kg"
    )

    observaciones = models.TextField(blank=True)

    ingreso_generado = models.OneToOneField(
        'contabilidad.Ingreso',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='residuo_origen'
    )

    class Meta:
        verbose_name = "Residuo Aceptado"
        verbose_name_plural = "Residuos Aceptados"
        ordering = ["-fecha_aceptacion"]

    def __str__(self):
        return f"Aceptado #{self.residuo_id} – {self.residuo.tipo}"
