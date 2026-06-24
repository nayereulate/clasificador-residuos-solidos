from decimal import Decimal

from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone


class PrecioMaterial(models.Model):
    """Tabla de precios de compra por material reciclable."""

    MATERIALES = [
        ("Metal",        "Metal"),
        ("Vidrio",       "Vidrio"),
        ("Plástico",     "Plástico"),
        ("Papel/Cartón", "Papel/Cartón"),
        ("Orgánico",     "Orgánico"),
        ("Espuma/EPS",   "Espuma/EPS"),
        ("Otro",         "Otro"),
    ]

    material = models.CharField(max_length=100, choices=MATERIALES, unique=True)
    precio_por_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "Precio de Material"
        verbose_name_plural = "Precios de Materiales"
        ordering = ["material"]

    def __str__(self):
        return f"{self.material} – ${self.precio_por_kg}/kg"


class CategoriaIngreso(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Categoría de Ingreso"
        verbose_name_plural = "Categorías de Ingreso"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Ingreso(models.Model):
    TIPOS = [
        ("venta_material", "Venta de material"),
        ("subsidio", "Subsidio"),
        ("donacion", "Donación"),
        ("otro", "Otro"),
    ]

    categoria = models.ForeignKey(
        CategoriaIngreso, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ingresos"
    )
    tipo = models.CharField(max_length=50, choices=TIPOS, default="venta_material")
    material = models.CharField(max_length=100, blank=True)
    cantidad_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_por_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descripcion = models.TextField(blank=True)
    fecha = models.DateField(default=date.today)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ingreso"
        verbose_name_plural = "Ingresos"
        ordering = ["-fecha", "-fecha_creacion"]

    def __str__(self):
        return f"Ingreso {self.get_tipo_display()} – ${self.monto_total} ({self.fecha})"

    def save(self, *args, **kwargs):
        if self.cantidad_kg and self.precio_por_kg:
            self.monto_total = (
                Decimal(str(self.cantidad_kg)) * Decimal(str(self.precio_por_kg))
            ).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


class CategoriaEgreso(models.Model):
    TIPOS = [
        ("transporte", "Transporte"),

        ("clasificacion", "Clasificación"),
        ("procesamiento", "Procesamiento"),
        ("mantenimiento", "Mantenimiento"),
        ("personal", "Personal"),
        ("otro", "Otro"),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPOS, default="otro")

    class Meta:
        verbose_name = "Categoría de Egreso"
        verbose_name_plural = "Categorías de Egreso"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class Egreso(models.Model):
    categoria = models.ForeignKey(
        CategoriaEgreso, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="egresos"
    )
    concepto = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    descripcion = models.TextField(blank=True)
    fecha = models.DateField(default=date.today)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Egreso"
        verbose_name_plural = "Egresos"
        ordering = ["-fecha", "-fecha_creacion"]

    def __str__(self):
        return f"{self.concepto} – ${self.monto} ({self.fecha})"
