from django.urls import path

# Módulo 1 – vistas existentes (sin cambios)
from .views import inicio, api_analizar_frame

# Módulo 2 – Administración
from .views_admin import (
    admin_dashboard,
    admin_procesar,
    admin_procesar_todos,
    admin_estado,
    admin_detalle,
    admin_exportar,
)

urlpatterns = [
    # ── Módulo 1 (intacto) ────────────────────────────────────────────────
    path("", inicio, name="inicio"),
    path("api/analizar-frame/", api_analizar_frame, name="api_analizar_frame"),

    # ── Módulo 2 – Administración ─────────────────────────────────────────
    path("administracion/",                        admin_dashboard,     name="admin_dashboard"),
    path("administracion/procesar/<int:pk>/",      admin_procesar,      name="admin_procesar"),
    path("administracion/procesar-todos/",         admin_procesar_todos, name="admin_procesar_todos"),
    path("administracion/estado/",                 admin_estado,        name="admin_estado"),
    path("administracion/detalle/<int:pk>/",       admin_detalle,       name="admin_detalle"),
    path("administracion/exportar/<str:formato>/", admin_exportar,      name="admin_exportar"),
]
