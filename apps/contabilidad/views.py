import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect

from .forms import IngresoForm, EgresoForm, PrecioMaterialForm
from .models import Ingreso, Egreso, CategoriaEgreso, PrecioMaterial


def _log(request, accion, descripcion, objeto=None):
    try:
        from apps.historial.utils import registrar
        registrar(request, accion, "contabilidad", descripcion, objeto)
    except Exception:
        pass


@login_required
def dashboard(request):
    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    total_ingresos_mes = (
        Ingreso.objects.filter(fecha__gte=inicio_mes)
        .aggregate(total=Sum("monto_total"))["total"] or Decimal("0")
    )
    total_egresos_mes = (
        Egreso.objects.filter(fecha__gte=inicio_mes)
        .aggregate(total=Sum("monto"))["total"] or Decimal("0")
    )
    utilidad_mes = total_ingresos_mes - total_egresos_mes

    total_ingresos_global = (
        Ingreso.objects.aggregate(total=Sum("monto_total"))["total"] or Decimal("0")
    )
    total_egresos_global = (
        Egreso.objects.aggregate(total=Sum("monto"))["total"] or Decimal("0")
    )
    utilidad_global = total_ingresos_global - total_egresos_global

    por_material = {}
    for ing in Ingreso.objects.filter(material__gt="").values("material").annotate(total=Sum("monto_total")):
        por_material[ing["material"]] = float(ing["total"])

    por_categoria = {}
    for eg in Egreso.objects.filter(categoria__isnull=False).values("categoria__tipo").annotate(total=Sum("monto")):
        por_categoria[eg["categoria__tipo"] or "otro"] = float(eg["total"])

    ultimos_ingresos = Ingreso.objects.select_related("categoria").order_by("-fecha")[:8]
    ultimos_egresos = Egreso.objects.select_related("categoria").order_by("-fecha")[:8]

    # Resumen de kg y monto por material con precio actual incluido
    precios_map = {p.material: float(p.precio_por_kg) for p in PrecioMaterial.objects.filter(activo=True)}
    resumen_material = []
    for ing in Ingreso.objects.filter(material__gt="", tipo="venta_material").values("material").annotate(
        total_monto=Sum("monto_total"),
        total_kg=Sum("cantidad_kg"),
    ).order_by("material"):
        mat = ing["material"]
        resumen_material.append({
            "material": mat,
            "monto": float(ing["total_monto"] or 0),
            "kg": float(ing["total_kg"] or 0),
            "precio_kg": precios_map.get(mat),
        })

    return render(request, "contabilidad/dashboard.html", {
        "total_ingresos_mes": total_ingresos_mes,
        "total_egresos_mes": total_egresos_mes,
        "utilidad_mes": utilidad_mes,
        "total_ingresos_global": total_ingresos_global,
        "total_egresos_global": total_egresos_global,
        "utilidad_global": utilidad_global,
        "por_material_json": json.dumps(por_material),
        "por_categoria_json": json.dumps(por_categoria),
        "ultimos_ingresos": ultimos_ingresos,
        "ultimos_egresos": ultimos_egresos,
        "resumen_material": resumen_material,
    })


@login_required
def lista_ingresos(request):
    qs = Ingreso.objects.select_related("categoria", "registrado_por").all()

    fecha_desde = request.GET.get("desde")
    fecha_hasta = request.GET.get("hasta")
    material = request.GET.get("material", "").strip()
    tipo = request.GET.get("tipo", "").strip()

    if fecha_desde:
        qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha__lte=fecha_hasta)
    if material:
        qs = qs.filter(material__icontains=material)
    if tipo:
        qs = qs.filter(tipo=tipo)

    total = qs.aggregate(total=Sum("monto_total"))["total"] or Decimal("0")

    return render(request, "contabilidad/ingreso_list.html", {
        "ingresos": qs,
        "total": total,
        "tipos": Ingreso.TIPOS,
    })


@login_required
def crear_ingreso(request):
    if request.method == "POST":
        form = IngresoForm(request.POST)
        if form.is_valid():
            ingreso = form.save(commit=False)
            ingreso.registrado_por = request.user
            ingreso.save()
            _log(request, "CREAR", f"Ingreso creado: ${ingreso.monto_total}", ingreso)
            return redirect("contabilidad:lista_ingresos")
    else:
        form = IngresoForm(initial={"fecha": date.today()})
    return render(request, "contabilidad/ingreso_form.html", {"form": form, "titulo": "Registrar Ingreso"})


@login_required
def editar_ingreso(request, pk):
    ingreso = get_object_or_404(Ingreso, pk=pk)
    if request.method == "POST":
        form = IngresoForm(request.POST, instance=ingreso)
        if form.is_valid():
            form.save()
            _log(request, "EDITAR", f"Ingreso #{pk} editado")
            return redirect("contabilidad:lista_ingresos")
    else:
        form = IngresoForm(instance=ingreso)
    return render(request, "contabilidad/ingreso_form.html", {"form": form, "titulo": "Editar Ingreso"})


@login_required
def eliminar_ingreso(request, pk):
    if request.method == "POST":
        ingreso = get_object_or_404(Ingreso, pk=pk)
        ingreso.delete()
        _log(request, "ELIMINAR", f"Ingreso #{pk} eliminado")
    return redirect("contabilidad:lista_ingresos")


@login_required
def lista_egresos(request):
    qs = Egreso.objects.select_related("categoria", "registrado_por").all()

    fecha_desde = request.GET.get("desde")
    fecha_hasta = request.GET.get("hasta")
    categoria = request.GET.get("categoria", "").strip()

    if fecha_desde:
        qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha__lte=fecha_hasta)
    if categoria:
        qs = qs.filter(categoria__tipo=categoria)

    total = qs.aggregate(total=Sum("monto"))["total"] or Decimal("0")

    return render(request, "contabilidad/egreso_list.html", {
        "egresos": qs,
        "total": total,
        "categorias": CategoriaEgreso.TIPOS,
    })


@login_required
def crear_egreso(request):
    if request.method == "POST":
        form = EgresoForm(request.POST)
        if form.is_valid():
            egreso = form.save(commit=False)
            egreso.registrado_por = request.user
            egreso.save()
            _log(request, "CREAR", f"Egreso creado: ${egreso.monto}", egreso)
            return redirect("contabilidad:lista_egresos")
    else:
        form = EgresoForm(initial={"fecha": date.today()})
    return render(request, "contabilidad/egreso_form.html", {"form": form, "titulo": "Registrar Egreso"})


@login_required
def editar_egreso(request, pk):
    egreso = get_object_or_404(Egreso, pk=pk)
    if request.method == "POST":
        form = EgresoForm(request.POST, instance=egreso)
        if form.is_valid():
            form.save()
            _log(request, "EDITAR", f"Egreso #{pk} editado")
            return redirect("contabilidad:lista_egresos")
    else:
        form = EgresoForm(instance=egreso)
    return render(request, "contabilidad/egreso_form.html", {"form": form, "titulo": "Editar Egreso"})


@login_required
def eliminar_egreso(request, pk):
    if request.method == "POST":
        egreso = get_object_or_404(Egreso, pk=pk)
        egreso.delete()
        _log(request, "ELIMINAR", f"Egreso #{pk} eliminado")
    return redirect("contabilidad:lista_egresos")


@login_required
def api_datos_grafico(request):
    hoy = date.today()
    inicio = (hoy.replace(day=1) - timedelta(days=150)).replace(day=1)

    ingresos_por_mes = (
        Ingreso.objects.filter(fecha__gte=inicio)
        .annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto_total"))
        .order_by("mes")
    )
    egresos_por_mes = (
        Egreso.objects.filter(fecha__gte=inicio)
        .annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto"))
        .order_by("mes")
    )

    meses_ing = {r["mes"].strftime("%Y-%m"): float(r["total"]) for r in ingresos_por_mes}
    meses_eg = {r["mes"].strftime("%Y-%m"): float(r["total"]) for r in egresos_por_mes}
    todas_claves = sorted(set(meses_ing) | set(meses_eg))

    return JsonResponse({
        "labels": todas_claves,
        "ingresos": [meses_ing.get(k, 0) for k in todas_claves],
        "egresos": [meses_eg.get(k, 0) for k in todas_claves],
    })


# ─────────────────────────────────────────────────────────────────────────────
# GESTIÓN DE PRECIOS POR MATERIAL
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def proyeccion(request):
    """
    Cruza Residuo + ResultadoAdministracion + ResiduoAceptado + PrecioMaterial
    para calcular peso medio, kg estimados e ingresos proyectados por material.
    Acepta filtro por fechas (tanda) o muestra el total histórico.
    """
    from apps.clasificacion.models import ResultadoAdministracion, ResiduoAceptado

    fecha_desde = request.GET.get("desde", "")
    fecha_hasta = request.GET.get("hasta", "")

    # ── 1. Precios configurados ────────────────────────────────────────────────
    precios_map = {
        p.material: float(p.precio_por_kg)
        for p in PrecioMaterial.objects.filter(activo=True)
    }

    # ── 2. Total de residuos por material + peso_medio_kg del grammar engine ──
    admin_qs = ResultadoAdministracion.objects.select_related("residuo")
    if fecha_desde:
        admin_qs = admin_qs.filter(residuo__fecha__date__gte=fecha_desde)
    if fecha_hasta:
        admin_qs = admin_qs.filter(residuo__fecha__date__lte=fecha_hasta)

    conteo_por_material = {}
    # peso medio del grammar engine: promedio ponderado de peso_medio_kg por material
    grammar_peso_sum   = {}
    grammar_peso_count = {}
    for a in admin_qs:
        mat = a.material_predominante
        conteo_por_material[mat] = conteo_por_material.get(mat, 0) + 1
        if a.peso_medio_kg and a.peso_medio_kg > 0:
            grammar_peso_sum[mat]   = grammar_peso_sum.get(mat, 0.0)   + a.peso_medio_kg
            grammar_peso_count[mat] = grammar_peso_count.get(mat, 0)   + 1

    # Peso medio genérico del grammar engine por material
    grammar_peso_medio = {
        mat: round(grammar_peso_sum[mat] / grammar_peso_count[mat], 4)
        for mat in grammar_peso_sum if grammar_peso_count[mat] > 0
    }

    # ── 3. Peso real de residuos ACEPTADOS (con filtro de fecha) ──────────────
    aceptados_qs = ResiduoAceptado.objects.select_related("residuo__administracion")
    if fecha_desde:
        aceptados_qs = aceptados_qs.filter(fecha_aceptacion__date__gte=fecha_desde)
    if fecha_hasta:
        aceptados_qs = aceptados_qs.filter(fecha_aceptacion__date__lte=fecha_hasta)

    # Agrupar por material → kg totales y peso medio real
    peso_por_material = {}
    for a in aceptados_qs:
        try:
            mat = a.residuo.administracion.material_predominante
        except Exception:
            continue
        kg = float(a.peso_kg or 0)
        if mat not in peso_por_material:
            peso_por_material[mat] = {"total_kg": 0.0, "count": 0}
        peso_por_material[mat]["total_kg"] += kg
        if kg > 0:
            peso_por_material[mat]["count"] += 1

    # ── 4. Ingresos reales registrados en contabilidad ────────────────────────
    ing_qs = Ingreso.objects.filter(tipo="venta_material", material__gt="")
    if fecha_desde:
        ing_qs = ing_qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        ing_qs = ing_qs.filter(fecha__lte=fecha_hasta)

    ingresos_reales_map = {}
    for ing in ing_qs.values("material").annotate(total=Sum("monto_total"), kg=Sum("cantidad_kg")):
        ingresos_reales_map[ing["material"]] = {
            "monto": float(ing["total"] or 0),
            "kg": float(ing["kg"] or 0),
        }

    # ── 5. Construir tabla por material ───────────────────────────────────────
    materiales_set = (
        set(conteo_por_material)
        | set(peso_por_material)
        | set(ingresos_reales_map)
        | set(precios_map)
    )

    tabla = []
    total_residuos    = 0
    total_kg_real     = 0.0
    total_kg_estimado = 0.0
    total_ing_real    = 0.0
    total_ing_estimado = 0.0

    for mat in sorted(materiales_set):
        count_reg  = conteo_por_material.get(mat, 0)
        pesos      = peso_por_material.get(mat, {"total_kg": 0.0, "count": 0})
        kg_real    = pesos["total_kg"]
        count_peso = pesos["count"]

        # Peso medio real (de aceptados con peso registrado)
        peso_medio_real = round(kg_real / count_peso, 3) if count_peso > 0 else 0.0

        # Fallback: peso medio genérico del grammar engine si no hay pesos reales
        peso_medio_grammar = grammar_peso_medio.get(mat, 0.0)
        usa_grammar        = peso_medio_real == 0.0 and peso_medio_grammar > 0

        peso_medio = peso_medio_real if peso_medio_real > 0 else peso_medio_grammar
        kg_est     = round(peso_medio * count_reg, 3) if peso_medio > 0 else 0.0

        precio    = precios_map.get(mat, 0.0)
        ing_est   = round(kg_est * precio, 2)
        ing_real_d = ingresos_reales_map.get(mat, {"monto": 0.0, "kg": 0.0})

        tabla.append({
            "material":             mat,
            "count_reg":            count_reg,
            "count_peso":           count_peso,
            "kg_real":              round(kg_real, 3),
            "peso_medio":           peso_medio,
            "peso_medio_grammar":   round(peso_medio_grammar, 4),
            "usa_grammar":          usa_grammar,
            "kg_estimado":          kg_est,
            "precio_kg":            precio,
            "ing_estimado":         ing_est,
            "ing_real":             ing_real_d["monto"],
            "kg_real_ing":          ing_real_d["kg"],
            "tiene_precio":         precio > 0,
        })

        total_residuos    += count_reg
        total_kg_real     += kg_real
        total_kg_estimado += kg_est
        total_ing_real    += ing_real_d["monto"]
        total_ing_estimado += ing_est

    # ── 6. Porcentajes para gráficos ──────────────────────────────────────────
    for row in tabla:
        row["pct_residuos"] = round(row["count_reg"] / total_residuos * 100, 1) if total_residuos else 0
        row["pct_ing_est"]  = round(row["ing_estimado"] / total_ing_estimado * 100, 1) if total_ing_estimado else 0
        row["pct_kg_est"]   = round(row["kg_estimado"] / total_kg_estimado * 100, 1) if total_kg_estimado else 0

    # ── 7. JSON para Chart.js ─────────────────────────────────────────────────
    labels       = [r["material"] for r in tabla]
    colores_base = ["#52b788","#3b82f6","#f59e0b","#ef4444","#8b5cf6","#06b6d4","#d97706"]
    colores      = [colores_base[i % len(colores_base)] for i in range(len(labels))]

    charts = {
        "labels":       labels,
        "colores":      colores,
        "pct_residuos": [r["pct_residuos"] for r in tabla],
        "pct_ing_est":  [r["pct_ing_est"]  for r in tabla],
        "kg_real":      [r["kg_real"]       for r in tabla],
        "kg_estimado":  [r["kg_estimado"]   for r in tabla],
        "ing_real":     [r["ing_real"]       for r in tabla],
        "ing_estimado": [r["ing_estimado"]   for r in tabla],
    }

    return render(request, "contabilidad/proyeccion.html", {
        "tabla":              tabla,
        "total_residuos":     total_residuos,
        "total_kg_real":      round(total_kg_real, 3),
        "total_kg_estimado":  round(total_kg_estimado, 3),
        "total_ing_real":     round(total_ing_real, 2),
        "total_ing_estimado": round(total_ing_estimado, 2),
        "charts_json":        json.dumps(charts),
        "fecha_desde":        fecha_desde,
        "fecha_hasta":        fecha_hasta,
        "sin_precios":        [r["material"] for r in tabla if not r["tiene_precio"] and r["count_reg"] > 0],
        "grammar_peso_medio": grammar_peso_medio,
        "usa_grammar_alguno": any(r["usa_grammar"] for r in tabla),
    })


@login_required
def lista_precios(request):
    precios = PrecioMaterial.objects.all()
    return render(request, "contabilidad/precios.html", {"precios": precios})


@login_required
def guardar_precio(request):
    """Crea o actualiza el precio de un material vía POST."""
    if request.method == "POST":
        material = request.POST.get("material", "").strip()
        precio_por_kg = request.POST.get("precio_por_kg", "0")
        notas = request.POST.get("notas", "")
        activo = request.POST.get("activo") == "on"

        if material:
            PrecioMaterial.objects.update_or_create(
                material=material,
                defaults={
                    "precio_por_kg": precio_por_kg,
                    "notas": notas,
                    "activo": activo,
                },
            )
            _log(request, "PRECIO", f"Precio actualizado: {material} → ${precio_por_kg}/kg")
    return redirect("contabilidad:lista_precios")
