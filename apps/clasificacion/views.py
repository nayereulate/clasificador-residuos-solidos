from pathlib import Path
import base64
import json
import os
import tempfile
import uuid

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from .forms import ResiduoForm
from .models import Residuo
from .services.yolo_service import detectar_objetos


def _log(request, accion, descripcion, objeto=None):
    try:
        from apps.historial.utils import registrar
        registrar(request, accion, 'clasificacion', descripcion, objeto)
    except Exception:
        pass


def _resumen_desde_resultado(resultado):
    detecciones = resultado.get("detecciones", [])
    objetos = resultado.get("objetos", {})
    total = resultado.get("total", resultado.get("cantidad_total", 0))
    imagen_procesada = resultado.get("imagen_procesada", "")
    boxes = resultado.get("boxes", [])

    if detecciones:
        objeto_principal = detecciones[0]["nombre"]
        confianza = max(item.get("confianza", 0) for item in detecciones)
    else:
        objeto_principal = "Sin detección"
        confianza = 0

    return {
        "objeto_principal": objeto_principal,
        "confianza": confianza,
        "objetos": objetos,
        "total": total,
        "cantidad_total": total,
        "imagen_procesada": imagen_procesada,
        "detecciones": detecciones,
        "boxes": boxes,
    }


@login_required
def inicio(request):
    """
    Vista principal.
    Permite subir una imagen y ver historial.
    """
    if request.method == "POST":
        form = ResiduoForm(request.POST, request.FILES)

        if form.is_valid():
            residuo = form.save()

            try:
                resultado = detectar_objetos(
                    residuo.imagen.path,
                    nombre_base=Path(residuo.imagen.name).stem,
                    imgsz=640,
                    guardar_imagen=True
                )

                resumen = _resumen_desde_resultado(resultado)

                residuo.tipo = resumen["objeto_principal"]
                residuo.categoria = "Pendiente"
                residuo.confianza = resumen["confianza"]
                residuo.resultado_json = {
                    "objetos": resumen["objetos"],
                    "total": resumen["total"],
                    "cantidad_total": resumen["cantidad_total"],
                    "detecciones": resumen["detecciones"],
                    "boxes": resumen["boxes"],
                    "imagen_procesada": resumen["imagen_procesada"],
                }
                residuo.save()
                _log(request, 'ANALIZAR',
                     f'Imagen analizada: {residuo.tipo} ({residuo.confianza:.2f})', residuo)

            except Exception as e:
                print("\n===== ERROR AL PROCESAR =====")
                print(e)
                print("=============================\n")

                residuo.tipo = "Error"
                residuo.categoria = "Error"
                residuo.confianza = 0
                residuo.resultado_json = {
                    "objetos": {},
                    "total": 0,
                    "cantidad_total": 0,
                    "detecciones": [],
                    "boxes": [],
                    "imagen_procesada": "",
                }
                residuo.save()

            return redirect("inicio")

    else:
        form = ResiduoForm()

    residuos = Residuo.objects.all().order_by("-fecha")
    ultimo_residuo = residuos.first()

    return render(
        request,
        "clasificacion/inicio.html",
        {
            "form": form,
            "residuos": residuos,
            "ultimo_residuo": ultimo_residuo
        }
    )


@csrf_exempt
def api_analizar_frame(request):
    """
    API para cámara en vivo.
    Recibe un frame en base64, lo analiza y devuelve JSON.
    Si guardar=true, además crea un registro en la BD.
    """
    if request.method != "POST":
        return JsonResponse(
            {"ok": False, "error": "Método no permitido"},
            status=405
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
        imagen_b64 = payload.get("image", "")
        guardar = bool(payload.get("guardar", False))

        if not imagen_b64:
            return JsonResponse(
                {"ok": False, "error": "No se recibió imagen"},
                status=400
            )

        if "," in imagen_b64:
            _, imagen_b64 = imagen_b64.split(",", 1)

        imagen_bytes = base64.b64decode(imagen_b64)
        nombre_base = f"camara_{uuid.uuid4().hex[:10]}"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(imagen_bytes)
            tmp_path = tmp.name

        try:
            resultado = detectar_objetos(
                tmp_path,
                nombre_base=nombre_base,
                imgsz=416,
                guardar_imagen=guardar
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        resumen = _resumen_desde_resultado(resultado)

        respuesta = {
            "objeto_principal": resumen["objeto_principal"],
            "confianza": resumen["confianza"],
            "objetos": resumen["objetos"],
            "cantidad_total": resumen["cantidad_total"],
            "total": resumen["total"],
            "boxes": resumen["boxes"],
            "imagen_procesada": resumen["imagen_procesada"],
            "material_predominante": "Pendiente",
            "materiales": {},
        }

        if guardar:
            residuo = Residuo()

            nombre_archivo = f"{nombre_base}.jpg"
            residuo.imagen.save(
                nombre_archivo,
                ContentFile(imagen_bytes),
                save=False
            )

            residuo.tipo = respuesta["objeto_principal"]
            residuo.categoria = "Pendiente"
            residuo.confianza = respuesta["confianza"]
            residuo.resultado_json = {
                "objetos": respuesta["objetos"],
                "total": respuesta["total"],
                "cantidad_total": respuesta["cantidad_total"],
                "boxes": respuesta["boxes"],
                "imagen_procesada": respuesta["imagen_procesada"],
            }
            residuo.save()

            respuesta["guardado"] = True
            respuesta["residuo"] = {
                "id": residuo.id,
                "tipo": residuo.tipo,
                "categoria": residuo.categoria,
                "confianza": residuo.confianza,
                "fecha": residuo.fecha.strftime("%d/%m/%Y %H:%M"),
                "imagen_url": residuo.imagen.url,
                "resultado_json": residuo.resultado_json,
            }

        return JsonResponse(
            {
                "ok": True,
                "resultado": respuesta
            }
        )

    except Exception as e:
        return JsonResponse(
            {
                "ok": False,
                "error": str(e)
            },
            status=500
        )