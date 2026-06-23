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

import cv2
import numpy as np

from .forms import ResiduoForm
from .models import Residuo
from .services.yolo_service import detectar_objetos, detectar_con_track, reset_tracker
from .services.tracker_service import get_cam_tracker, reset_cam_tracker
from .services import video_service


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


@csrf_exempt
def api_analizar_frame_v2(request):
    """
    Cámara en vivo con ByteTrack persistente.
    POST JSON: { image: <base64>, guardar: bool, reset: bool }
    Retorna tracks con clase dominante y conteo único de objetos.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

    try:
        payload     = json.loads(request.body.decode("utf-8"))
        imagen_b64  = payload.get("image", "")
        guardar     = bool(payload.get("guardar", False))
        do_reset    = bool(payload.get("reset", False))

        if not imagen_b64:
            return JsonResponse({"ok": False, "error": "No se recibió imagen"}, status=400)

        if "," in imagen_b64:
            _, imagen_b64 = imagen_b64.split(",", 1)

        imagen_bytes = base64.b64decode(imagen_b64)

        # Decodificar a numpy para ByteTrack (sin guardar en disco)
        nparr = np.frombuffer(imagen_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return JsonResponse({"ok": False, "error": "No se pudo decodificar imagen"}, status=400)

        # Reset tracker al iniciar nueva sesión
        if do_reset:
            reset_tracker()
            reset_cam_tracker()

        detecciones_raw = detectar_con_track(frame)
        tracker         = get_cam_tracker()
        detecciones     = tracker.update(detecciones_raw)

        conteo_unico  = tracker.get_conteo_unico()
        total_unicos  = tracker.get_total_unicos()

        objeto_principal = (
            max(conteo_unico, key=conteo_unico.get) if conteo_unico else "Sin detección"
        )
        confianza_max = max(
            (d["confianza_promedio"] for d in detecciones), default=0.0
        )

        boxes = [
            {
                "x1":        d["x1"],
                "y1":        d["y1"],
                "x2":        d["x2"],
                "y2":        d["y2"],
                "label":     d["clase_dominante"],
                "track_id":  d.get("track_id"),
                "confianza": d["confianza_promedio"],
                "color":     "#00c853",
            }
            for d in detecciones
        ]

        respuesta = {
            "objeto_principal":    objeto_principal,
            "confianza":           round(confianza_max, 4),
            "objetos":             conteo_unico,
            "cantidad_total":      total_unicos,
            "total":               total_unicos,
            "boxes":               boxes,
            "imagen_procesada":    "",
            "material_predominante": "Pendiente",
            "materiales":          {},
            "total_unicos":        total_unicos,
            "conteo_unico":        conteo_unico,
            "tracks_activos":      len(detecciones),
        }

        if guardar:
            nombre_base  = f"camara_{uuid.uuid4().hex[:10]}"
            nombre_archivo = f"{nombre_base}.jpg"
            residuo = Residuo()
            residuo.imagen.save(nombre_archivo, ContentFile(imagen_bytes), save=False)
            residuo.tipo      = objeto_principal
            residuo.categoria = "Pendiente"
            residuo.confianza = confianza_max
            residuo.resultado_json = {
                "objetos":          conteo_unico,
                "total":            total_unicos,
                "cantidad_total":   total_unicos,
                "boxes":            boxes,
                "imagen_procesada": "",
            }
            residuo.save()
            _log(request, "ANALIZAR",
                 f"Frame cámara guardado (ByteTrack): {objeto_principal}", residuo)
            respuesta["guardado"] = True
            respuesta["residuo"]  = {
                "id":            residuo.id,
                "tipo":          residuo.tipo,
                "categoria":     residuo.categoria,
                "confianza":     residuo.confianza,
                "fecha":         residuo.fecha.strftime("%d/%m/%Y %H:%M"),
                "imagen_url":    residuo.imagen.url,
                "resultado_json": residuo.resultado_json,
            }

        return JsonResponse({"ok": True, "resultado": respuesta})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@csrf_exempt
def api_procesar_video(request):
    """
    Recibe un archivo de video (multipart/form-data, campo 'video'),
    lo guarda en un temporal y lanza el procesamiento en un hilo daemon.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

    archivo = request.FILES.get("video")
    if not archivo:
        return JsonResponse({"ok": False, "error": "No se recibió archivo de video"}, status=400)

    sufijo = Path(archivo.name).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufijo) as tmp:
        for chunk in archivo.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    video_service.iniciar_procesamiento_video(tmp_path)
    return JsonResponse({"ok": True, "mensaje": "Procesando video en segundo plano"})


def api_estado_video(request):
    """Retorna el estado actual del procesamiento de video."""
    return JsonResponse(video_service.get_estado_video())