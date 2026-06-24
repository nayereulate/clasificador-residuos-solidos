from django.urls import path

# Módulo 1 – vistas existentes (sin cambios)
from .views import (inicio, api_analizar_frame, api_analizar_frame_v2,
                    api_procesar_video, api_estado_video)

# Módulo 2 – Administración
from .views_admin import (
    admin_dashboard,
    admin_procesar,
    admin_procesar_todos,
    admin_estado,
    admin_detalle,
    admin_exportar,
    admin_aceptados,
    admin_aceptar,
    admin_rechazar,
    admin_eliminar,
    admin_eliminar_pendientes,
)

urlpatterns = [
    # ── Módulo 1 (intacto) ────────────────────────────────────────────────
    path("", inicio, name="inicio"),
    path("api/analizar-frame/",    api_analizar_frame,    name="api_analizar_frame"),
    path("api/analizar-frame/v2/", api_analizar_frame_v2, name="api_analizar_frame_v2"),
    path("api/procesar-video/",  api_procesar_video,  name="api_procesar_video"),
    path("api/estado-video/",    api_estado_video,    name="api_estado_video"),

    # ── Módulo 2 – Administración ─────────────────────────────────────────
    path("administracion/",                        admin_dashboard,      name="admin_dashboard"),
    path("administracion/procesar/<int:pk>/",      admin_procesar,       name="admin_procesar"),
    path("administracion/procesar-todos/",         admin_procesar_todos, name="admin_procesar_todos"),
    path("administracion/estado/",                 admin_estado,         name="admin_estado"),
    path("administracion/detalle/<int:pk>/",       admin_detalle,        name="admin_detalle"),
    path("administracion/exportar/<str:formato>/", admin_exportar,       name="admin_exportar"),
    path("administracion/aceptados/",              admin_aceptados,           name="admin_aceptados"),
    path("administracion/aceptar/<int:pk>/",       admin_aceptar,             name="admin_aceptar"),
    path("administracion/rechazar/<int:pk>/",      admin_rechazar,            name="admin_rechazar"),
    path("administracion/eliminar/<int:pk>/",      admin_eliminar,            name="admin_eliminar"),
    path("administracion/eliminar-pendientes/",    admin_eliminar_pendientes, name="admin_eliminar_pendientes"),
]
