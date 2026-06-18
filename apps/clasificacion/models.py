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

    fecha_procesado = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Admin #{self.residuo_id} – {self.material_predominante} [{self.prioridad}]"
