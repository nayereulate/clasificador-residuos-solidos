from django.urls import path
from . import views

urlpatterns = [
    path('recoleccion/',                      views.lista_rutas,    name='rutas_lista'),
    path('recoleccion/crear/',                views.crear_ruta,     name='rutas_crear'),
    path('recoleccion/<int:pk>/',             views.detalle_ruta,   name='rutas_detalle'),
    path('recoleccion/<int:pk>/editar/',      views.editar_ruta,    name='rutas_editar'),
    path('recoleccion/<int:pk>/eliminar/',    views.eliminar_ruta,  name='rutas_eliminar'),
    path('recoleccion/<int:pk>/estado/',      views.cambiar_estado, name='rutas_estado'),
    path('recoleccion/<int:pk>/residuo/',     views.asignar_residuo, name='rutas_residuo'),
]
