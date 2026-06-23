from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/',  admin.site.urls),

    # Módulos de la aplicación
    path('', include('apps.clasificacion.urls')),
    path('', include('apps.usuarios.urls')),
    path('', include('apps.historial.urls')),
    path('', include('apps.reportes.urls')),
    path('', include('apps.recoleccion.urls')),
    path('', include('apps.contabilidad.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
