from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('administrador', 'Administrador'),
        ('operador',      'Operador'),
    ]

    rol = models.CharField(
        max_length=20,
        choices=ROL_CHOICES,
        default='operador',
        verbose_name='Rol',
    )
    departamento = models.CharField(max_length=100, blank=True, verbose_name='Departamento')
    telefono     = models.CharField(max_length=20,  blank=True, verbose_name='Teléfono')

    class Meta:
        verbose_name          = 'Usuario'
        verbose_name_plural   = 'Usuarios'
        ordering              = ['first_name', 'last_name', 'username']

    def __str__(self):
        full = self.get_full_name()
        return full if full.strip() else self.username

    @property
    def es_admin(self):
        return self.rol == 'administrador' or self.is_superuser

    @property
    def iniciales(self):
        fn = self.first_name[:1].upper() if self.first_name else ''
        ln = self.last_name[:1].upper()  if self.last_name  else ''
        return (fn + ln) or self.username[:2].upper()
