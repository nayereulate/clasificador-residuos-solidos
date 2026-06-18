from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.clasificacion.models import Residuo
from .forms import RutaForm, ZonaForm
from .models import RutaRecoleccion, Zona


# ─── Lista de rutas ───────────────────────────────────────────────────────────

@login_required
def lista_rutas(request):
    qs = RutaRecoleccion.objects.select_related('zona', 'operador').prefetch_related('residuos')

    estado    = request.GET.get('estado', '')
    prioridad = request.GET.get('prioridad', '')
    zona_id   = request.GET.get('zona', '')
    q         = request.GET.get('q', '')

    if estado:    qs = qs.filter(estado=estado)
    if prioridad: qs = qs.filter(prioridad=prioridad)
    if zona_id:   qs = qs.filter(zona_id=zona_id)
    if q:         qs = qs.filter(nombre__icontains=q)

    paginator = Paginator(qs, 20)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    # Contadores rápidos
    totales = {
        'pendiente':  RutaRecoleccion.objects.filter(estado='pendiente').count(),
        'en_proceso': RutaRecoleccion.objects.filter(estado='en_proceso').count(),
        'completada': RutaRecoleccion.objects.filter(estado='completada').count(),
        'cancelada':  RutaRecoleccion.objects.filter(estado='cancelada').count(),
    }

    return render(request, 'recoleccion/lista.html', {
        'page_obj':  page_obj,
        'estado':    estado,
        'prioridad': prioridad,
        'zona_id':   zona_id,
        'q':         q,
        'zonas':     Zona.objects.all(),
        'totales':   totales,
    })


# ─── Crear ruta ───────────────────────────────────────────────────────────────

@login_required
def crear_ruta(request):
    if request.method == 'POST':
        form = RutaForm(request.POST)
        if form.is_valid():
            ruta = form.save()
            try:
                from apps.historial.utils import registrar
                registrar(request, 'CREAR', 'recoleccion',
                          f'Ruta creada: {ruta.nombre}', ruta)
            except Exception:
                pass
            messages.success(request, f'Ruta "{ruta.nombre}" creada correctamente.')
            return redirect('rutas_lista')
    else:
        form = RutaForm()

    return render(request, 'recoleccion/form.html', {
        'form': form, 'modo': 'crear',
    })


# ─── Editar ruta ──────────────────────────────────────────────────────────────

@login_required
def editar_ruta(request, pk):
    ruta = get_object_or_404(RutaRecoleccion, pk=pk)

    if request.method == 'POST':
        form = RutaForm(request.POST, instance=ruta)
        if form.is_valid():
            ruta = form.save()
            try:
                from apps.historial.utils import registrar
                registrar(request, 'EDITAR', 'recoleccion',
                          f'Ruta editada: {ruta.nombre}', ruta)
            except Exception:
                pass
            messages.success(request, f'Ruta "{ruta.nombre}" actualizada.')
            return redirect('rutas_lista')
    else:
        form = RutaForm(instance=ruta)

    return render(request, 'recoleccion/form.html', {
        'form': form, 'modo': 'editar', 'ruta': ruta,
    })


# ─── Detalle de ruta ──────────────────────────────────────────────────────────

@login_required
def detalle_ruta(request, pk):
    ruta = get_object_or_404(
        RutaRecoleccion.objects.select_related('zona', 'operador')
                               .prefetch_related('residuos__administracion'),
        pk=pk,
    )
    # Residuos no asignados a esta ruta para el selector
    asignados_ids = ruta.residuos.values_list('pk', flat=True)
    disponibles   = Residuo.objects.exclude(pk__in=asignados_ids).order_by('-fecha')[:50]

    return render(request, 'recoleccion/detalle.html', {
        'ruta':        ruta,
        'disponibles': disponibles,
    })


# ─── Cambiar estado (AJAX) ────────────────────────────────────────────────────

@login_required
@require_POST
def cambiar_estado(request, pk):
    ruta   = get_object_or_404(RutaRecoleccion, pk=pk)
    estado = request.POST.get('estado', '')

    if estado not in dict(RutaRecoleccion.ESTADOS):
        return JsonResponse({'ok': False, 'error': 'Estado inválido.'}, status=400)

    ruta.estado = estado
    if estado == 'completada':
        ruta.fecha_completada = timezone.now()
    ruta.save(update_fields=['estado', 'fecha_completada'])

    try:
        from apps.historial.utils import registrar
        registrar(request, 'EDITAR', 'recoleccion',
                  f'Estado de ruta {ruta.nombre} cambiado a {estado}.', ruta)
    except Exception:
        pass

    return JsonResponse({'ok': True, 'nuevo_estado': ruta.get_estado_display()})


# ─── Asignar / desasignar residuos (AJAX) ────────────────────────────────────

@login_required
@require_POST
def asignar_residuo(request, pk):
    ruta      = get_object_or_404(RutaRecoleccion, pk=pk)
    residuo_id = request.POST.get('residuo_id')
    accion     = request.POST.get('accion', 'agregar')  # 'agregar' | 'quitar'

    try:
        residuo = Residuo.objects.get(pk=residuo_id)
    except Residuo.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Residuo no encontrado.'}, status=404)

    if accion == 'agregar':
        ruta.residuos.add(residuo)
        msg = f'Residuo #{residuo.id} agregado a la ruta.'
    else:
        ruta.residuos.remove(residuo)
        msg = f'Residuo #{residuo.id} quitado de la ruta.'

    return JsonResponse({'ok': True, 'mensaje': msg, 'total': ruta.total_residuos})


# ─── Eliminar ruta ────────────────────────────────────────────────────────────

@login_required
def eliminar_ruta(request, pk):
    ruta = get_object_or_404(RutaRecoleccion, pk=pk)
    if request.method == 'POST':
        nombre = str(ruta)
        ruta.delete()
        try:
            from apps.historial.utils import registrar
            registrar(request, 'ELIMINAR', 'recoleccion', f'Ruta eliminada: {nombre}')
        except Exception:
            pass
        messages.success(request, 'Ruta eliminada.')
    return redirect('rutas_lista')
