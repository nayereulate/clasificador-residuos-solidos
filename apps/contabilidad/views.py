import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect

from .forms import IngresoForm, EgresoForm
from .models import Ingreso, Egreso, CategoriaEgreso


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
