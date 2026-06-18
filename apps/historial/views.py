from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
import datetime

from .models import EntradaHistorial


@login_required
def historial_view(request):
    qs = EntradaHistorial.objects.select_related('usuario').all()

    # Filtros
    accion  = request.GET.get('accion', '')
    modulo  = request.GET.get('modulo', '')
    usuario = request.GET.get('usuario', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    if accion:
        qs = qs.filter(accion=accion)
    if modulo:
        qs = qs.filter(modulo=modulo)
    if usuario:
        qs = qs.filter(usuario__username__icontains=usuario)
    if fecha_desde:
        try:
            qs = qs.filter(fecha__date__gte=datetime.date.fromisoformat(fecha_desde))
        except ValueError:
            pass
    if fecha_hasta:
        try:
            qs = qs.filter(fecha__date__lte=datetime.date.fromisoformat(fecha_hasta))
        except ValueError:
            pass

    # Paginación
    paginator = Paginator(qs, 30)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    # Estadísticas rápidas
    hoy = timezone.now().date()
    stats = {
        'hoy':      EntradaHistorial.objects.filter(fecha__date=hoy).count(),
        'semana':   EntradaHistorial.objects.filter(
                        fecha__date__gte=hoy - datetime.timedelta(days=7)).count(),
        'total':    EntradaHistorial.objects.count(),
        'usuarios': EntradaHistorial.objects.values('usuario').distinct().count(),
    }

    return render(request, 'historial/historial.html', {
        'page_obj':    page_obj,
        'accion':      accion,
        'modulo':      modulo,
        'usuario_q':   usuario,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'stats':       stats,
        'acciones':    EntradaHistorial.ACCIONES,
        'modulos':     EntradaHistorial.MODULOS,
    })


@login_required
def historial_api_count(request):
    """Devuelve el total de entradas para el badge del sidebar."""
    hoy   = timezone.now().date()
    count = EntradaHistorial.objects.filter(fecha__date=hoy).count()
    return JsonResponse({'count': count})
