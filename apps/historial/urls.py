from django.urls import path
from . import views

urlpatterns = [
    path('historial/',       views.historial_view,       name='historial'),
    path('historial/count/', views.historial_api_count,  name='historial_count'),
]
