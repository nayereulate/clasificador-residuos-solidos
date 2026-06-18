from django.urls import path
from . import views

urlpatterns = [
    path('reportes/',                  views.dashboard,         name='reportes_dashboard'),
    path('reportes/api/materiales/',   views.api_materiales,    name='reportes_api_materiales'),
    path('reportes/api/temporal/',     views.api_temporal,      name='reportes_api_temporal'),
    path('reportes/api/prioridades/',  views.api_prioridades,   name='reportes_api_prioridades'),
    path('reportes/api/confianza/',    views.api_confianza,     name='reportes_api_confianza'),
    path('reportes/excel/',            views.exportar_excel,    name='reportes_excel'),
    path('reportes/imprimir/',         views.imprimir_reporte,  name='reportes_imprimir'),
]
