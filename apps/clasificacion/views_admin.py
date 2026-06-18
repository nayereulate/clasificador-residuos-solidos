"""
Módulo 2 – Vistas de Administración
Todas las vistas leen de resultado_json; YOLO no se vuelve a ejecutar.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from .models import Residuo, ResultadoAdministracion
from .administracion_service import (
    AdministracionService,
    MATERIAL_COLORS,
    PRIORITY_COLORS,
    iniciar_hilo_procesamiento,
    get_estado_procesamiento,
)

_service = AdministracionService()


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def _log(request, accion, descripcion, objeto=None):
    try:
        from apps.historial.utils import registrar
        registrar(request, accion, 'administracion', descripcion, objeto)
    except Exception:
        pass


@login_required
def admin_dashboard(request):
    filtro_material  = request.GET.get("material",  "")
    filtro_prioridad = request.GET.get("prioridad", "")

    residuos_qs = Residuo.objects.all().order_by("-fecha")

    items = []
    pares_para_cola = []

    for r in residuos_qs:
        try:
            admin = r.administracion
        except ResultadoAdministracion.DoesNotExist:
            admin = None

        # Filtros
        if filtro_material and (not admin or admin.material_predominante != filtro_material):
            continue
        if filtro_prioridad and (not admin or admin.prioridad != filtro_prioridad):
            continue

        items.append({
            "residuo":      r,
            "admin":        admin,
            "mat_color":    MATERIAL_COLORS.get(admin.material_predominante, "secondary") if admin else "secondary",
            "prio_color":   PRIORITY_COLORS.get(admin.prioridad, "secondary") if admin else "secondary",
        })
        pares_para_cola.append((r, admin))

    # Cola de prioridad (solo registros ya analizados)
    pares_analizados = [(r, a) for r, a in pares_para_cola if a is not None]
    cola_ordenada = _service.construir_cola_prioridad(pares_analizados)

    # Estadísticas generales
    total_residuos   = Residuo.objects.count()
    total_analizados = ResultadoAdministracion.objects.count()
    pendientes       = total_residuos - total_analizados

    materiales_count = {}
    for a in ResultadoAdministracion.objects.all():
        m = a.material_predominante
        materiales_count[m] = materiales_count.get(m, 0) + 1

    alertas_recientes = []
    for a in ResultadoAdministracion.objects.select_related("residuo").order_by("-fecha_procesado")[:20]:
        for texto in a.alertas:
            alertas_recientes.append({"texto": texto, "residuo_id": a.residuo_id})
            if len(alertas_recientes) >= 8:
                break
        if len(alertas_recientes) >= 8:
            break

    materiales_disponibles = list(
        ResultadoAdministracion.objects
        .values_list("material_predominante", flat=True)
        .distinct()
        .order_by("material_predominante")
    )

    return render(request, "clasificacion/administracion.html", {
        "items":                  items,
        "cola_ordenada":          cola_ordenada[:10],
        "total_residuos":         total_residuos,
        "total_analizados":       total_analizados,
        "pendientes":             pendientes,
        "materiales_count":       materiales_count,
        "alertas_recientes":      alertas_recientes,
        "materiales_disponibles": materiales_disponibles,
        "filtro_material":        filtro_material,
        "filtro_prioridad":       filtro_prioridad,
        "estado_proc":            get_estado_procesamiento(),
        "MATERIAL_COLORS":        MATERIAL_COLORS,
        "PRIORITY_COLORS":        PRIORITY_COLORS,
    })


# ─────────────────────────────────────────────────────────────────────────────
# PROCESAR UN RESIDUO INDIVIDUAL
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def admin_procesar(request, pk):
    residuo   = get_object_or_404(Residuo, pk=pk)
    resultado = _service.procesar_residuo(residuo)

    ResultadoAdministracion.objects.update_or_create(
        residuo=residuo,
        defaults={
            "material_predominante": resultado["material_predominante"],
            "materiales":            resultado["materiales"],
            "prioridad":             resultado["prioridad"],
            "nivel_prioridad":       resultado["nivel_prioridad"],
            "alertas":               resultado["alertas"],
            "resultado_grammar":     resultado["resultado_grammar"],
        },
    )

    if residuo.categoria in ("Pendiente", ""):
        residuo.categoria = resultado["material_predominante"]
        residuo.save(update_fields=["categoria"])

    _log(request, 'PROCESAR',
         f'Residuo #{residuo.id} procesado: {resultado["material_predominante"]}', residuo)

    return redirect("admin_dashboard")


# ─────────────────────────────────────────────────────────────────────────────
# PROCESAR TODOS (hilo de fondo)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def admin_procesar_todos(request):
    if request.method == "POST":
        ya_procesados = set(
            ResultadoAdministracion.objects.values_list("residuo_id", flat=True)
        )
        pendientes_ids = list(
            Residuo.objects.exclude(pk__in=ya_procesados).values_list("pk", flat=True)
        )
        if pendientes_ids:
            iniciar_hilo_procesamiento(pendientes_ids)
    return redirect("admin_dashboard")


# ─────────────────────────────────────────────────────────────────────────────
# ESTADO DEL HILO (AJAX)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def admin_estado(request):
    return JsonResponse(get_estado_procesamiento())


# ─────────────────────────────────────────────────────────────────────────────
# DETALLE DE UN RESIDUO (Grammar Engine output)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def admin_detalle(request, pk):
    residuo = get_object_or_404(Residuo, pk=pk)
    try:
        admin = residuo.administracion
    except ResultadoAdministracion.DoesNotExist:
        admin = None

    return render(request, "clasificacion/admin_detalle.html", {
        "residuo":       residuo,
        "admin":         admin,
        "mat_color":     MATERIAL_COLORS.get(admin.material_predominante, "secondary") if admin else "secondary",
        "prio_color":    PRIORITY_COLORS.get(admin.prioridad, "secondary") if admin else "secondary",
        "MATERIAL_COLORS": MATERIAL_COLORS,
    })


# ─────────────────────────────────────────────────────────────────────────────
# EXPORTACIÓN  (JSON / XML / TXT)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def admin_exportar(request, formato):
    if formato not in ("json", "xml", "txt"):
        return HttpResponse("Formato no soportado.", status=400)

    admins_qs = (
        ResultadoAdministracion.objects
        .select_related("residuo")
        .order_by("nivel_prioridad", "-fecha_procesado")
    )

    registros = {}
    for a in admins_qs:
        key = f"residuo_{a.residuo_id}"
        registros[key] = {
            "id":                    a.residuo_id,
            "fecha_captura":         a.residuo.fecha.strftime("%Y-%m-%d %H:%M:%S"),
            "tipo_objeto":           a.residuo.tipo,
            "material_predominante": a.material_predominante,
            "materiales":            a.materiales,
            "prioridad":             a.prioridad,
            "nivel_prioridad":       a.nivel_prioridad,
            "alertas":               a.alertas,
            "fecha_procesado":       a.fecha_procesado.strftime("%Y-%m-%d %H:%M:%S"),
        }

    data = {
        "fecha_exportacion": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_registros":   admins_qs.count(),
        "registros":         registros,
    }

    contenido = _service.exportar(formato, data)

    content_types = {
        "json": "application/json",
        "xml":  "application/xml",
        "txt":  "text/plain",
    }

    response = HttpResponse(contenido, content_type=f"{content_types[formato]}; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="administracion_{timezone.now().strftime("%Y%m%d_%H%M%S")}.{formato}"'
    )
    _log(request, 'EXPORTAR', f'Exportación {formato.upper()} generada ({admins_qs.count()} registros).')
    return response
