"""
Módulo 2 – Vistas de Administración
Todas las vistas leen de resultado_json; YOLO no se vuelve a ejecutar.
"""

import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from .models import Residuo, ResultadoAdministracion, ResiduoAceptado
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
    filtro_material    = request.GET.get("material",    "")
    filtro_prioridad   = request.GET.get("prioridad",   "")
    filtro_fecha_desde = request.GET.get("fecha_desde", "")
    filtro_fecha_hasta = request.GET.get("fecha_hasta", "")

    residuos_qs = Residuo.objects.select_related(
        "administracion", "aceptado"
    ).order_by("-fecha")

    if filtro_fecha_desde:
        residuos_qs = residuos_qs.filter(fecha__date__gte=filtro_fecha_desde)
    if filtro_fecha_hasta:
        residuos_qs = residuos_qs.filter(fecha__date__lte=filtro_fecha_hasta)

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

        objetos_raw = (r.resultado_json or {}).get("objetos") or {}
        items.append({
            "residuo":      r,
            "admin":        admin,
            "mat_color":    MATERIAL_COLORS.get(admin.material_predominante, "secondary") if admin else "secondary",
            "prio_color":   PRIORITY_COLORS.get(admin.prioridad, "secondary") if admin else "secondary",
            "objetos_json": json.dumps(objetos_raw, ensure_ascii=False),
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
        "filtro_fecha_desde":     filtro_fecha_desde,
        "filtro_fecha_hasta":     filtro_fecha_hasta,
        "count_sin_clasificar":   Residuo.objects.filter(
            administracion__material_predominante="Sin clasificar"
        ).count(),
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
            "peso_medio_kg":         resultado["peso_medio_kg"],
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


# ─────────────────────────────────────────────────────────────────────────────
# BASE DE DATOS GENERAL: residuos aceptados por administración
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def admin_aceptados(request):
    """Vista general de todos los residuos aceptados por administración."""
    filtro_material   = request.GET.get("material",    "")
    filtro_fecha_desde = request.GET.get("fecha_desde", "")
    filtro_fecha_hasta = request.GET.get("fecha_hasta", "")

    qs = ResiduoAceptado.objects.select_related(
        "residuo", "residuo__administracion", "aceptado_por", "ingreso_generado"
    ).order_by("-fecha_aceptacion")

    if filtro_material:
        qs = qs.filter(residuo__administracion__material_predominante=filtro_material)
    if filtro_fecha_desde:
        qs = qs.filter(fecha_aceptacion__date__gte=filtro_fecha_desde)
    if filtro_fecha_hasta:
        qs = qs.filter(fecha_aceptacion__date__lte=filtro_fecha_hasta)

    from .administracion_service import MATERIAL_PRIORITY_LABEL
    materiales_disponibles = list(
        ResiduoAceptado.objects
        .filter(residuo__administracion__isnull=False)
        .values_list("residuo__administracion__material_predominante", flat=True)
        .distinct()
        .order_by("residuo__administracion__material_predominante")
    )

    return render(request, "clasificacion/admin_aceptados.html", {
        "aceptados":              qs,
        "total":                  qs.count(),
        "materiales_disponibles": materiales_disponibles,
        "filtro_material":        filtro_material,
        "filtro_fecha_desde":     filtro_fecha_desde,
        "filtro_fecha_hasta":     filtro_fecha_hasta,
        "MATERIAL_COLORS":        MATERIAL_COLORS,
        "PRIORITY_COLORS":        PRIORITY_COLORS,
    })


@login_required
def admin_aceptar(request, pk):
    """Acepta un residuo y opcionalmente genera un ingreso en contabilidad."""
    if request.method != "POST":
        return redirect("admin_dashboard")

    residuo = get_object_or_404(Residuo, pk=pk)
    peso_kg = request.POST.get("peso_kg", "0") or "0"
    observaciones = request.POST.get("observaciones", "")

    try:
        peso = max(0.0, float(peso_kg))
    except (ValueError, TypeError):
        peso = 0.0

    aceptado, _ = ResiduoAceptado.objects.get_or_create(
        residuo=residuo,
        defaults={
            "aceptado_por": request.user,
            "peso_kg": peso,
            "observaciones": observaciones,
        }
    )
    if not _:
        aceptado.peso_kg = peso
        aceptado.observaciones = observaciones
        aceptado.save(update_fields=["peso_kg", "observaciones"])

    # Auto-generar ingreso en contabilidad si hay precio configurado
    if aceptado.ingreso_generado is None:
        try:
            from apps.contabilidad.models import Ingreso, PrecioMaterial
            material = ""
            try:
                material = residuo.administracion.material_predominante
            except Exception:
                pass

            precio_obj = PrecioMaterial.objects.filter(material=material, activo=True).first()
            precio_kg = precio_obj.precio_por_kg if precio_obj else 0

            ingreso = Ingreso.objects.create(
                tipo="venta_material",
                material=material,
                cantidad_kg=peso,
                precio_por_kg=precio_kg,
                descripcion=f"Ingreso automático – Residuo #{residuo.id} ({residuo.tipo})",
                registrado_por=request.user,
            )
            aceptado.ingreso_generado = ingreso
            aceptado.save(update_fields=["ingreso_generado"])
            _log(request, "ACEPTAR",
                 f"Residuo #{residuo.id} aceptado. Ingreso ${ingreso.monto_total} generado.", residuo)
        except Exception as e:
            _log(request, "ACEPTAR",
                 f"Residuo #{residuo.id} aceptado (sin ingreso: {e}).", residuo)
    else:
        _log(request, "ACEPTAR", f"Residuo #{residuo.id} actualizado.", residuo)

    return redirect(request.POST.get("next", "admin_aceptados"))


@login_required
def admin_rechazar(request, pk):
    """Elimina el registro de aceptado (rechaza el residuo)."""
    if request.method == "POST":
        ResiduoAceptado.objects.filter(residuo_id=pk).delete()
        _log(request, "RECHAZAR", f"Residuo #{pk} rechazado.")
    return redirect("admin_aceptados")


# ─────────────────────────────────────────────────────────────────────────────
# ELIMINAR RESIDUOS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def admin_eliminar(request, pk):
    """Elimina un residuo individual (y su archivo de imagen)."""
    if request.method == "POST":
        residuo = get_object_or_404(Residuo, pk=pk)
        try:
            if residuo.imagen and residuo.imagen.path:
                import os
                if os.path.exists(residuo.imagen.path):
                    os.remove(residuo.imagen.path)
        except Exception:
            pass
        residuo.delete()
        _log(request, "ELIMINAR", f"Residuo #{pk} eliminado.")
    return redirect("admin_dashboard")


@login_required
def admin_eliminar_pendientes(request):
    """Elimina residuos cuyo resultado del Grammar Engine es 'Sin clasificar'
    (no se detectó ningún material reconocible)."""
    if request.method == "POST":
        import os
        qs = Residuo.objects.filter(
            administracion__material_predominante="Sin clasificar"
        )
        count = qs.count()
        for r in qs:
            try:
                if r.imagen and r.imagen.path and os.path.exists(r.imagen.path):
                    os.remove(r.imagen.path)
            except Exception:
                pass
        qs.delete()
        _log(request, "ELIMINAR", f"{count} residuos 'Sin clasificar' eliminados.")
    return redirect("admin_dashboard")
