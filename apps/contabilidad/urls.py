from django.urls import path
from . import views

app_name = "contabilidad"

urlpatterns = [
    path("contabilidad/",                           views.dashboard,         name="dashboard"),
    path("contabilidad/ingresos/",                  views.lista_ingresos,    name="lista_ingresos"),
    path("contabilidad/ingresos/crear/",            views.crear_ingreso,     name="crear_ingreso"),
    path("contabilidad/ingresos/<int:pk>/editar/",  views.editar_ingreso,    name="editar_ingreso"),
    path("contabilidad/ingresos/<int:pk>/eliminar/",views.eliminar_ingreso,  name="eliminar_ingreso"),
    path("contabilidad/egresos/",                   views.lista_egresos,     name="lista_egresos"),
    path("contabilidad/egresos/crear/",             views.crear_egreso,      name="crear_egreso"),
    path("contabilidad/egresos/<int:pk>/editar/",   views.editar_egreso,     name="editar_egreso"),
    path("contabilidad/egresos/<int:pk>/eliminar/", views.eliminar_egreso,   name="eliminar_egreso"),
    path("contabilidad/api/grafico/",               views.api_datos_grafico, name="api_grafico"),
    path("contabilidad/precios/",                   views.lista_precios,     name="lista_precios"),
    path("contabilidad/precios/guardar/",           views.guardar_precio,    name="guardar_precio"),
    path("contabilidad/proyeccion/",                views.proyeccion,        name="proyeccion"),
]
