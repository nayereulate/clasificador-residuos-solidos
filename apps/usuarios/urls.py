from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('auth/login/',  views.login_view,  name='login'),
    path('auth/logout/', views.logout_view, name='logout'),

    # Perfil
    path('perfil/',              views.perfil_view,          name='perfil'),
    path('perfil/password/',     views.cambiar_password_view, name='cambiar_password'),

    # Gestión de usuarios (admin)
    path('usuarios/',                 views.lista_usuarios,  name='usuarios_lista'),
    path('usuarios/crear/',           views.crear_usuario,   name='usuarios_crear'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario,  name='usuarios_editar'),
    path('usuarios/<int:pk>/eliminar/', views.eliminar_usuario, name='usuarios_eliminar'),
]
